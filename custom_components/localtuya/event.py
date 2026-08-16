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
"""

import logging
from functools import partial
from typing import override

import voluptuous as vol
from homeassistant.components.event import DOMAIN, EventDeviceClass, EventEntity
from homeassistant.const import CONF_DEVICE_ID

from .const import FINGERBOT_BUTTON_EVENT
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


async_setup_entry = partial(async_setup_entry, DOMAIN, LocalTuyaEvent, flow_schema)
