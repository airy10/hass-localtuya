"""Platform to locally control Tuya-based button devices."""

import logging
from functools import partial
from .config_flow import col_to_select
from homeassistant.helpers.selector import ObjectSelector

import voluptuous as vol
from homeassistant.const import CONF_DEVICE_CLASS
from homeassistant.components.humidifier import (
    DOMAIN,
    HumidifierDeviceClass,
    DEVICE_CLASSES_SCHEMA,
    HumidifierEntity,
    HumidifierEntityDescription,
    HumidifierEntityFeature,
)
from homeassistant.components.humidifier.const import (
    ATTR_MAX_HUMIDITY,
    ATTR_MIN_HUMIDITY,
    DEFAULT_MAX_HUMIDITY,
    DEFAULT_MIN_HUMIDITY,
)

from .const import (
    CONF_HUMIDIFIER_SET_HUMIDITY_DP,
    CONF_HUMIDIFIER_CURRENT_HUMIDITY_DP,
    CONF_HUMIDIFIER_MODE_DP,
    CONF_HUMIDIFIER_AVAILABLE_MODES,
    DictSelector,
)

from .entity import LocalTuyaEntity, async_setup_entry
from .core.dp_wrappers import RawDPWrapper, dp_wrapper_by_id


_LOGGER = logging.getLogger(__name__)


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(CONF_HUMIDIFIER_SET_HUMIDITY_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_HUMIDIFIER_CURRENT_HUMIDITY_DP): col_to_select(
            dps, is_dps=True
        ),
        vol.Optional(CONF_HUMIDIFIER_MODE_DP): col_to_select(dps, is_dps=True),
        vol.Required(ATTR_MIN_HUMIDITY, default=DEFAULT_MIN_HUMIDITY): int,
        vol.Required(ATTR_MAX_HUMIDITY, default=DEFAULT_MAX_HUMIDITY): int,
        vol.Optional(CONF_HUMIDIFIER_AVAILABLE_MODES, default={}): ObjectSelector(),
        vol.Optional(CONF_DEVICE_CLASS): DEVICE_CLASSES_SCHEMA,
    }


class LocalTuyaHumidifier(LocalTuyaEntity, HumidifierEntity):
    """Representation of a Localtuya Humidifier."""

    _dp_mode = CONF_HUMIDIFIER_MODE_DP
    _available_modes = CONF_HUMIDIFIER_AVAILABLE_MODES
    _dp_current_humidity = CONF_HUMIDIFIER_CURRENT_HUMIDITY_DP
    _dp_set_humidity = CONF_HUMIDIFIER_SET_HUMIDITY_DP
    _mode_name_to_value = {}

    def __init__(
        self,
        device,
        config_entry,
        humidifierID,
        **kwargs,
    ):
        """Initialize the Tuya button."""
        super().__init__(device, config_entry, humidifierID, _LOGGER, **kwargs)
        self._state = None

        # Cloud spec wrappers for the configured DPs (core parity); DPs with
        # no cloud spec fall back to a raw wrapper so reads/writes always
        # delegate through the wrapper layer.
        self._switch_wrapper = dp_wrapper_by_id(
            device, self._dp_id
        ) or RawDPWrapper(self._dp_id)
        self._target_humidity_wrapper = (
            dp_wrapper_by_id(device, self._config.get(self._dp_set_humidity))
            or RawDPWrapper(self._config.get(self._dp_set_humidity))
        ) if self.has_config(self._dp_set_humidity) else None
        self._current_humidity_wrapper = (
            dp_wrapper_by_id(device, self._config.get(self._dp_current_humidity))
            or RawDPWrapper(self._config.get(self._dp_current_humidity))
        ) if self.has_config(self._dp_current_humidity) else None
        self._mode_wrapper = (
            dp_wrapper_by_id(device, self._config.get(self._dp_mode))
            or RawDPWrapper(self._config.get(self._dp_mode))
        ) if self.has_config(self._dp_mode) else None

        if (modes := self._config.get(self._available_modes, {})) and (
            self._config.get(self._dp_mode)
        ):
            self._attr_supported_features |= HumidifierEntityFeature.MODES
            modes = {
                k: v if k else v.replace("_", " ").capitalize()
                for k, v in modes.copy().items()
            }
        self._available_modes = DictSelector(modes)

        self._attr_min_humidity = self._config.get(
            ATTR_MIN_HUMIDITY, DEFAULT_MIN_HUMIDITY
        )
        self._attr_max_humidity = self._config.get(
            ATTR_MAX_HUMIDITY, DEFAULT_MAX_HUMIDITY
        )

    @property
    def is_on(self) -> bool:
        """Return the device is on or off."""
        return self._read_wrapper(self._switch_wrapper)

    @property
    def mode(self) -> str | None:
        """Return the current mode."""
        return self._available_modes.to_ha(
            self._read_wrapper(self._mode_wrapper), "unknown"
        )

    @property
    def target_humidity(self) -> int | None:
        """Return the humidity we try to reach."""
        return self._read_wrapper(self._target_humidity_wrapper)

    @property
    def current_humidity(self) -> int | None:
        """Return the current humidity."""
        return self._read_wrapper(self._current_humidity_wrapper)

    async def async_turn_on(self, **kwargs):
        """Turn the device on."""
        await self._async_send_wrapper_updates(self._switch_wrapper, True)

    async def async_turn_off(self, **kwargs):
        """Turn the device off."""
        await self._async_send_wrapper_updates(self._switch_wrapper, False)

    async def async_set_humidity(self, humidity: int) -> None:
        """Set new target humidity."""
        await self._async_send_wrapper_updates(
            self._target_humidity_wrapper, humidity
        )

    async def async_set_mode(self, mode):
        """Set new target preset mode."""
        await self._async_send_wrapper_updates(
            self._mode_wrapper, self._available_modes.to_tuya(mode)
        )

    @property
    def available_modes(self):
        """Return the list of presets that this device supports."""
        return self._available_modes.names

async_setup_entry = partial(async_setup_entry, DOMAIN, LocalTuyaHumidifier, flow_schema)
