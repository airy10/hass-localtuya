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
        ``localtuya_fingerbot_button_pressed`` bus event (no DP exists for it);
        the auto-created ``LocalTuyaFingerbotButtonEvent`` is its per-report
        successor, sharing the datapoint-report base with the unlock events.
      - BLE unlock attribution (``LocalTuyaBLEUnlockEvent``) is a standalone
        per-datapoint-report entity ported from ha_tuya_ble bea2520 — see
        ARCHITECTURE_ALIGNMENT_CORE_TUYA.md §7.12. These report-driven
        entities are intentionally NOT LocalTuyaEntity and NOT table-driven;
        do not "migrate" them into the description flow during core syncs.
"""

import logging
from functools import partial
from typing import override

import voluptuous as vol
from homeassistant.components.event import DOMAIN
from homeassistant.components.event import EventDeviceClass, EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICE_ID
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN as LOCALTUYA_DOMAIN
from .const import FINGERBOT_BUTTON_EVENT, LOCALTUYA_DISCOVERY_NEW
from .coordinator import HassLocalTuyaData, TuyaDevice

EVENT_DOMAIN = DOMAIN
from .core.definitions import get_event_definition
from .core.quirks import QUIRKS_REGISTRY
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


class _LocalTuyaBLEReportEvent(EventEntity):
    """Base for event entities driven by raw BLE datapoint reports.

    Ported from ha_tuya_ble commit bea2520. Deliberately not a
    LocalTuyaEntity: the status dispatcher only carries value changes, while
    these entities fire on every report (a repeated unlock or press must be
    a new event).
    """

    _attr_should_poll = False

    def __init__(
        self,
        device: TuyaDevice,
        config_entry: ConfigEntry,
        unique_id_suffix: str,
        dp_events: dict[int, str],
    ) -> None:
        """Initialize the report-driven event entity."""
        self._tuya_device = device
        dev_cfg = device._device_config
        self._attr_unique_id = f"local_{dev_cfg.id}_{unique_id_suffix}"
        self._attr_has_entity_name = True
        self._attr_device_info = DeviceInfo(
            identifiers={(LOCALTUYA_DOMAIN, f"local_{dev_cfg.id}")},
            name=dev_cfg.name,
            manufacturer="Tuya",
            model=f"{dev_cfg.model} ({dev_cfg.id})",
        )
        self._dp_events = dp_events
        self._attr_event_types = sorted(set(dp_events.values()))
        # Datapoints whose first report on the current connection was already
        # seen and discarded as replayed history.
        self._seen_replays: set[int] = set()

    @property
    def available(self) -> bool:
        """Return whether the BLE connection is up."""
        return self._tuya_device.connected

    async def async_added_to_hass(self) -> None:
        """Start listening for datapoint reports."""
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
        """Expect replayed status again once the device comes back.

        Every connection begins with a status query, so the replay happens on
        each reconnection and not only at startup.
        """
        self._seen_replays.clear()

    @callback
    def _accepts(self, datapoint) -> bool:
        """Return whether a reported datapoint may fire an event."""
        return True

    @callback
    def _event_type_for(self, datapoint) -> str | None:
        """Return the event type for a datapoint, or None."""
        return self._dp_events.get(datapoint.id)

    @callback
    def _event_data(self, datapoint) -> dict:
        """Return the event payload."""
        return {}

    @callback
    def _handle_report(self, datapoints) -> None:
        """Turn datapoint reports into events."""
        for datapoint in datapoints:
            if not self._accepts(datapoint):
                continue
            event_type = self._event_type_for(datapoint)
            if event_type is None:
                continue

            # Connecting asks the device for its whole status, and it answers
            # with the last value of every datapoint - history rather than an
            # event, and the receive timestamp cannot tell them apart. The
            # first report of each datapoint per connection is dropped, at
            # the cost of missing a real event in the first seconds of a
            # connection.
            if datapoint.id not in self._seen_replays:
                self._seen_replays.add(datapoint.id)
                continue

            # Fired on every report, not only when the value changes.
            self._trigger_event(event_type, self._event_data(datapoint))
            self.async_write_ha_state()


class LocalTuyaBLEUnlockEvent(_LocalTuyaBLEReportEvent):
    """Fires whenever a BLE lock reports how it was opened.

    Also created for products that report unlocks but expose nothing to
    control, so they get no lock entity.
    """

    _attr_translation_key = "unlocked"

    def __init__(self, device: TuyaDevice, config_entry: ConfigEntry) -> None:
        """Initialize the unlock-attribution event entity."""
        capabilities = device.lock_capabilities
        super().__init__(
            device,
            config_entry,
            "unlocked",
            dict(capabilities.unlock_records) if capabilities else {},
        )

    @callback
    def _event_data(self, datapoint) -> dict:
        """Describe the credential the lock named."""
        return {ATTR_CREDENTIAL_ID: datapoint.value}


class LocalTuyaFingerbotButtonEvent(_LocalTuyaBLEReportEvent):
    """Fires whenever a Fingerbot's physical button press is reported.

    The per-report successor of the ``localtuya_fingerbot_button_pressed``
    bus event (which keeps firing for manually configured event entities);
    uses the same quirk-resolved button datapoint.
    """

    _attr_translation_key = "fingerbot_button"

    def __init__(
        self, device: TuyaDevice, config_entry: ConfigEntry, dp_id: int
    ) -> None:
        """Initialize the Fingerbot button event entity."""
        super().__init__(device, config_entry, f"button_{dp_id}", {dp_id: "pressed"})

    @callback
    def _accepts(self, datapoint) -> bool:
        """Only physical presses count; ignore echoes of our own writes."""
        return datapoint.changed_by_device

    @callback
    def _event_data(self, datapoint) -> dict:
        """Match the bus-event payload for automations parity."""
        return {CONF_DEVICE_ID: self._tuya_device.id}


_dp_events_setup = partial(async_setup_entry, EVENT_DOMAIN, LocalTuyaEvent, flow_schema)


def _report_event_entities(
    device: TuyaDevice, config_entry: ConfigEntry, created: set[str]
) -> list[EventEntity]:
    """Create the BLE report-driven entities this device qualifies for."""
    entities: list[EventEntity] = []
    unlock_key = f"{device.device_key}#unlock"
    capabilities = device.lock_capabilities
    if (
        capabilities is not None
        and capabilities.reports_unlocks
        and unlock_key not in created
    ):
        created.add(unlock_key)
        entities.append(LocalTuyaBLEUnlockEvent(device, config_entry))

    ble_device = device.ble_device
    quirk = QUIRKS_REGISTRY.get_quirk_for_device(ble_device) if ble_device else None
    button_key = f"{device.device_key}#button"
    if quirk is not None and quirk.button_switch_dp is not None:
        if button_key not in created:
            created.add(button_key)
            entities.append(
                LocalTuyaFingerbotButtonEvent(
                    device, config_entry, quirk.button_switch_dp
                )
            )
    return entities


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up DP-driven events plus BLE report-driven events."""
    await _dp_events_setup(hass, config_entry, async_add_entities)

    hass_entry_data: HassLocalTuyaData = hass.data[LOCALTUYA_DOMAIN][
        config_entry.entry_id
    ]
    created: set[str] = set()

    initial = []
    for device in hass_entry_data.devices.values():
        initial.extend(_report_event_entities(device, config_entry, created))
    if initial:
        async_add_entities(initial)

    @callback
    def _async_discover_device(device_keys: list[str]) -> None:
        """Create events for BLE devices that became available at runtime."""
        discovered = []
        for key in device_keys:
            device = hass_entry_data.devices.get(key)
            if device is None:
                continue
            discovered.extend(_report_event_entities(device, config_entry, created))
        if discovered:
            async_add_entities(discovered)

    config_entry.async_on_unload(
        async_dispatcher_connect(hass, LOCALTUYA_DISCOVERY_NEW, _async_discover_device)
    )
