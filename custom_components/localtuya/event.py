"""Platform to locally expose Tuya event entities.

BLE Fingerbot devices already fire ``localtuya_fingerbot_button_pressed``
on the HA bus (coordinator ``_handle_fingerbot_button``) when the physical
button is pressed; this platform wraps that bus event as an ``event``
entity (mirroring core tuya's event platform, which turns doorbell/button
DP updates into ``EventEntity`` triggers).
"""

import logging
from functools import partial

import voluptuous as vol
from homeassistant.components.event import DOMAIN, EventDeviceClass, EventEntity
from homeassistant.const import CONF_DEVICE_ID

from .const import FINGERBOT_BUTTON_EVENT
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
        **kwargs,
    ):
        """Initialize the Tuya event entity."""
        super().__init__(device, config_entry, eventid, _LOGGER, **kwargs)

    async def async_added_to_hass(self):
        """Subscribe to the fingerbot button event on the HA bus."""
        await super().async_added_to_hass()

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