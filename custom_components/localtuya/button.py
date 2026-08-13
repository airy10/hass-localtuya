"""Platform to locally control Tuya-based button devices."""

import logging
from functools import partial

import voluptuous as vol
from homeassistant.components.button import DOMAIN, ButtonEntity

from .entity import LocalTuyaEntity, async_setup_entry
from .const import CONF_PASSIVE_ENTITY
from .core.dp_wrappers import dp_wrapper_by_id

_LOGGER = logging.getLogger(__name__)


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        # vol.Required(CONF_PASSIVE_ENTITY): bool,
    }


class LocalTuyaButton(LocalTuyaEntity, ButtonEntity):
    """Representation of a Tuya button."""

    def __init__(
        self,
        device,
        config_entry,
        buttonid,
        **kwargs,
    ):
        """Initialize the Tuya button."""
        super().__init__(device, config_entry, buttonid, _LOGGER, **kwargs)
        self._state = None
        self._dpcode_wrapper = dp_wrapper_by_id(self._device, self._dp_id)

    async def async_press(self):
        """Press the button."""
        if self._dpcode_wrapper:
            await self._async_send_wrapper_updates(self._dpcode_wrapper, True)
        else:
            await self._device.set_dp(True, self._dp_id)


async_setup_entry = partial(async_setup_entry, DOMAIN, LocalTuyaButton, flow_schema)
