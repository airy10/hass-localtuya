"""Platform to present any Tuya DP as an enumeration."""

import logging
from functools import partial

import voluptuous as vol
from homeassistant.components.select import DOMAIN, SelectEntity
from homeassistant.const import CONF_DEVICE_CLASS, STATE_UNKNOWN
from homeassistant.helpers import selector

from .entity import LocalTuyaEntity, async_setup_entry
from .const import (
    CONF_DEFAULT_VALUE,
    CONF_OPTIONS,
    CONF_PASSIVE_ENTITY,
    CONF_RESTORE_ON_RECONNECT,
    DictSelector,
)
from .core.dp_wrappers import RawDPWrapper, dp_wrapper_by_id


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Required(CONF_OPTIONS, default={}): selector.ObjectSelector(),
        vol.Required(CONF_RESTORE_ON_RECONNECT): bool,
        vol.Required(CONF_PASSIVE_ENTITY): bool,
        vol.Optional(CONF_DEFAULT_VALUE): str,
    }


_LOGGER = logging.getLogger(__name__)


class LocalTuyaSelect(LocalTuyaEntity, SelectEntity):
    """Representation of a Tuya Enumeration."""

    def __init__(
        self,
        device,
        config_entry,
        sensorid,
        **kwargs,
    ):
        """Initialize the Tuya sensor."""
        super().__init__(device, config_entry, sensorid, _LOGGER, **kwargs)
        self._state = STATE_UNKNOWN
        self._state_friendly = ""
        self._dpcode_wrapper = dp_wrapper_by_id(self._device, self._dp_id) or RawDPWrapper(
            self._dp_id
        )

        # Set Display options
        options = {}
        config_options: dict = self._config.get(CONF_OPTIONS, {})
        if not isinstance(config_options, dict):
            self.warning(
                f"{self.name} DPiD: {self._dp_id}: Options configured incorrectly!"
                + "It must be in the format of key-value pairs,"
                + "where each line follows the structure [device_value: friendly name]"
            )
            config_options = {}
        if not config_options:
            # Cloud spec (core enum range) as default options source.
            if getattr(self._dpcode_wrapper, "options", None):
                config_options = {opt: opt for opt in self._dpcode_wrapper.options}
        for k, v in config_options.items():
            options[k] = str(v) if v else k.replace("_", "").capitalize()

        self._options = DictSelector(options)

    @property
    def current_option(self) -> str:
        """Return the selected entity option to represent the entity state."""
        value = self._read_wrapper(self._dpcode_wrapper)
        if value is not None:
            return self._options.to_ha(value, value)
        return self._state_friendly

    async def _process_device_update(
        self,
        updated_status_properties: list[str],
        dp_timestamps: dict[str, int] | None,
    ) -> bool:
        """Called when Tuya device sends an update with updated properties.

        Returns True if the Home Assistant state should be written,
        or False if the state write should be skipped.
        """
        return not self._dpcode_wrapper.skip_update(
            self._device, updated_status_properties, dp_timestamps
        )

    @property
    def options(self) -> list:
        """Return the list of values."""
        return self._options.names

    @property
    def device_class(self):
        """Return the class of this device."""
        return self._config.get(CONF_DEVICE_CLASS)

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        option_value = self._options.to_tuya(option)
        self.debug("Sending Option: " + option + " -> " + option_value)
        await self._async_send_wrapper_updates(self._dpcode_wrapper, option_value)

    def status_updated(self):
        """Device status was updated."""
        super().status_updated()

        if (state := self.dp_value(self._dp_id)) is not None:
            self._state_friendly = self._options.to_ha(state, state)

    # Default value is the first option
    def entity_default_value(self):
        """Return the first option as the default value for this entity type."""
        return self._options.names[0]


async_setup_entry = partial(async_setup_entry, DOMAIN, LocalTuyaSelect, flow_schema)
