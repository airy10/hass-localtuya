"""Platform to locally expose Tuya event entities.

Core parity: ``LocalTuyaEvent`` mirrors ``homeassistant/components/tuya/event.py``
(``TuyaEventEntity``).

SYNC CHECKLIST (when the core component is updated):
  1. Diff ``homeassistant/components/tuya/event.py`` against this file.
  2. Port: event-type declaration and ``_process_device_update``.
  3. Keep our deliberate deltas (they are intentional):
     - transport: reads go over BLE/Ethernet via ``_read_wrapper`` instead of
       cloud MQTT.
     - construction: ``__init__(device, config_entry, dp_id, description=None)``
       resolves the event wrapper by dpcode via ``get_event_definition``; the
       manual ``dps`` config (Fingerbot bus event) is the fallback.
      - ``unique_id`` stays ``local_{device_id}_{dp_id}`` (avoids orphaning).
      - BLE Fingerbot devices additionally wrap the
        ``localtuya_fingerbot_button_pressed`` bus event (no DP exists for it).
      - BLE unlock attribution (``LocalTuyaBLEUnlockEvent``) is a standalone
        per-datapoint-report entity ported from ha_tuya_ble bea2520 — see
        ARCHITECTURE_ALIGNMENT_CORE_TUYA.md §7.12. It is intentionally NOT a
        LocalTuyaEntity and NOT table-driven; do not "migrate" it into the
        description flow during core syncs.
"""

import logging
from functools import partial
from typing import override

import voluptuous as vol
from homeassistant.components.event import DOMAIN, EventDeviceClass, EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICE_ID
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import FINGERBOT_BUTTON_EVENT, LOCALTUYA_DISCOVERY_NEW
from .coordinator import HassLocalTuyaData, TuyaDevice
from .core.definitions import get_event_definition
from .entity import LocalTuyaEntity, async_setup_entry

_LOGGER = logging.getLogger(__name__)


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        # vol.Optional(CONF_PASSIVE_ENTITY): bool,
    }


class LocalTuyaEvent(LocalTuyaEntity, EventEntity):
    """Representation of a Tuya event entity."""

    _attr_device_class = EventDeviceClass.BUTTON
    _attr_event_types = ["pressed"]

    def __init__(
        self,
        device,
        config_entry,
        eventid,
        description=None,
        **kwargs,
    ):
        """Initialize the Tuya event entity."""
        super().__init__(device, config_entry, eventid, _LOGGER, **kwargs)
        self._dpcode_wrapper = None
        if description is not None:
            definition = get_event_definition(device, description)
            if definition is not None:
                self._dpcode_wrapper = definition.event_wrapper
                self._attr_event_types = self._dpcode_wrapper.options
                self._attr_device_class = self._config.get(CONF_DEVICE_CLASS)

    @override
    async def _process_device_update(
        self,
        updated_status_properties: list[str],
        dp_timestamps: dict[str, int] | None,
    ) -> bool:
        """Called when Tuya device sends an update with updated properties.

        Returns True if the Home Assistant state should be written,
        or False if the state write should be skipped.
        """
        if self._dpcode_wrapper is None:
            return True
        if self._dpcode_wrapper.skip_update(
            self._device, updated_status_properties, dp_timestamps
        ) or not (event_data := self._dpcode_wrapper.read_device_status(self._device)):
            return False

        event_type, event_attributes = event_data
        self._trigger_event(event_type, event_attributes)
        return True

    async def async_added_to_hass(self):
        """Subscribe to the fingerbot button event on the HA bus."""
        await super().async_added_to_hass()

        if self._dpcode_wrapper is not None:
            return

        self.async_on_remove(
            self.hass.bus.async_listen(
                FINGERBOT_BUTTON_EVENT, self._handle_fingerbot_button_event
            )
        )

    async def _handle_fingerbot_button_event(self, event) -> None:
        """Trigger the event entity when the device's button was pressed."""
        if event.data.get(CONF_DEVICE_ID) != self._device_config.id:
            return
        self._trigger_event("pressed", {CONF_DEVICE_ID: self._device_config.id})


ATTR_CREDENTIAL_ID = "credential_id"


class LocalTuyaBLEUnlockEvent(EventEntity):
    """Fires whenever a BLE lock reports how it was opened.

    Ported from ha_tuya_ble commit bea2520. Deliberately not a
    LocalTuyaEntity: it is driven by raw datapoint reports rather than the
    status dispatcher (a repeated unlock value must fire again), and it is
    also created for products that report unlocks but expose nothing to
    control, so they get no lock entity.
    """

    _attr_should_poll = False
    _attr_translation_key = "unlocked"

    def __init__(self, device: TuyaDevice, config_entry: ConfigEntry) -> None:
        """Initialize the unlock-attribution event entity."""
        self._tuya_device = device
        dev_cfg = device._device_config
        self._attr_unique_id = f"local_{dev_cfg.id}_unlocked"
        self._attr_has_entity_name = True
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"local_{dev_cfg.id}")},
            name=dev_cfg.name,
            manufacturer="Tuya",
            model=f"{dev_cfg.model} ({dev_cfg.id})",
        )
        capabilities = device.lock_capabilities
        self._dp_events = dict(capabilities.unlock_records)
        self._attr_event_types = sorted(set(self._dp_events.values()))
        # Datapoints whose first report on the current connection was already
        # seen and discarded as replayed history.
        self._seen_replays: set[int] = set()

    @property
    def available(self) -> bool:
        """Return whether the BLE connection is up."""
        return self._tuya_device.connected

    async def async_added_to_hass(self) -> None:
        """Start listening for unlock reports."""
        await super().async_added_to_hass()
        ble_device = self._tuya_device.ble_device
        if ble_device is None:
            return
        self.async_on_remove(ble_device.register_callback(self._handle_report))
        self.async_on_remove(
            ble_device.register_disconnected_callback(self._handle_disconnect)
        )

    @callback
    def _handle_disconnect(self) -> None:
        """Expect replayed status again once the lock comes back.

        Every connection begins with a status query, so the replay happens on
        each reconnection and not only at startup.
        """
        self._seen_replays.clear()

    @callback
    def _handle_report(self, datapoints) -> None:
        """Turn an unlock report into an event."""
        for datapoint in datapoints:
            event_type = self._dp_events.get(datapoint.id)
            if event_type is None:
                continue

            # Connecting asks the lock for its whole status, and the lock
            # answers with the last value of every datapoint - history rather
            # than an event, and the receive timestamp cannot tell them apart.
            # The first report of each datapoint per connection is dropped, at
            # the cost of missing an unlock in the first seconds of a
            # connection.
            if datapoint.id not in self._seen_replays:
                self._seen_replays.add(datapoint.id)
                continue

            # Fired on every report, not only when the value changes: the same
            # finger opening the door twice has to be two events.
            self._trigger_event(event_type, {ATTR_CREDENTIAL_ID: datapoint.value})
            self.async_write_ha_state()


_dp_events_setup = partial(async_setup_entry, DOMAIN, LocalTuyaEvent, flow_schema)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up DP-driven events plus BLE lock unlock-attribution events."""
    await _dp_events_setup(hass, config_entry, async_add_entities)

    hass_entry_data: HassLocalTuyaData = hass.data[DOMAIN][config_entry.entry_id]
    created: set[str] = set()

    def _maybe_create(device: TuyaDevice) -> LocalTuyaBLEUnlockEvent | None:
        if (
            device.lock_capabilities is None
            or not device.lock_capabilities.reports_unlocks
        ):
            return None
        if device.device_key in created:
            return None
        created.add(device.device_key)
        return LocalTuyaBLEUnlockEvent(device, config_entry)

    initial = []
    for device in hass_entry_data.devices.values():
        if entity := _maybe_create(device):
            initial.append(entity)
    if initial:
        async_add_entities(initial)

    @callback
    def _async_discover_device(device_keys: list[str]) -> None:
        """Create the event for BLE locks that became available at runtime."""
        discovered = []
        for key in device_keys:
            device = hass_entry_data.devices.get(key)
            if device is None:
                continue
            if entity := _maybe_create(device):
                discovered.append(entity)
        if discovered:
            async_add_entities(discovered)

    config_entry.async_on_unload(
        async_dispatcher_connect(hass, LOCALTUYA_DISCOVERY_NEW, _async_discover_device)
    )
