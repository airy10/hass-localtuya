"""Platform to locally control Tuya-based valve devices."""

import logging
from functools import partial

import voluptuous as vol
from homeassistant.components.valve import (
    DOMAIN,
    ValveDeviceClass,
    ValveEntity,
    ValveEntityFeature,
)

from .const import CONF_RESTORE_ON_RECONNECT
from .core.dp_wrappers import dp_wrapper_by_id
from .entity import LocalTuyaEntity, async_setup_entry

_LOGGER = logging.getLogger(__name__)


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Required(CONF_RESTORE_ON_RECONNECT): bool,
    }


class LocalTuyaValve(LocalTuyaEntity, ValveEntity):
    """Representation of a Tuya valve."""

    _attr_device_class = ValveDeviceClass.WATER
    _attr_supported_features = ValveEntityFeature.OPEN | ValveEntityFeature.CLOSE

    def __init__(
        self,
        device,
        config_entry,
        valveid,
        **kwargs,
    ):
        """Initialize the Tuya valve."""
        super().__init__(device, config_entry, valveid, _LOGGER, **kwargs)
        self._state = None
        self._dpcode_wrapper = dp_wrapper_by_id(device, self._dp_id)

    @property
    def is_closed(self) -> bool | None:
        """Return if the valve is closed."""
        if self._dpcode_wrapper:
            if (is_open := self._read_wrapper(self._dpcode_wrapper)) is None:
                return None
            return not is_open
        if (is_open := self._state) is None:
            return None
        return not is_open

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
        return not self._dpcode_wrapper.skip_update(
            self._device, updated_status_properties, dp_timestamps
        )

    async def async_open_valve(self) -> None:
        """Open the valve."""
        if self._dpcode_wrapper:
            await self._async_send_wrapper_updates(self._dpcode_wrapper, True)
            return
        await self._device.set_dp(True, self._dp_id)

    async def async_close_valve(self) -> None:
        """Close the valve."""
        if self._dpcode_wrapper:
            await self._async_send_wrapper_updates(self._dpcode_wrapper, False)
            return
        await self._device.set_dp(False, self._dp_id)


async_setup_entry = partial(async_setup_entry, DOMAIN, LocalTuyaValve, flow_schema)