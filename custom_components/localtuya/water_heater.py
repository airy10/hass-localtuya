"""Platform to locally control Tuya-based water-heater devices.

No core equivalent: the HA core ``tuya`` integration has no water-heater
platform (localtuya-only). No sync checklist applies. Keep the manual ``dps``
config fallback, the description-driven ``__init__``
(SPEC_DEFINITION_DRIVEN_RUNTIME.md), and the ``DictSelector`` / temperature
wrapper decorators.
"""

import logging
from functools import partial
from .config_flow import col_to_select
from homeassistant.helpers.selector import ObjectSelector

import voluptuous as vol
from homeassistant.components.water_heater import (
    DEFAULT_MIN_TEMP,
    DEFAULT_MAX_TEMP,
    DOMAIN,
    WaterHeaterEntity,
    WaterHeaterEntityFeature,
)
from homeassistant.components.water_heater.const import (
    STATE_ECO,
    STATE_ELECTRIC,
    STATE_PERFORMANCE,
    STATE_HIGH_DEMAND,
    STATE_HEAT_PUMP,
    STATE_GAS,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_TEMPERATURE_UNIT,
    PRECISION_HALVES,
    PRECISION_TENTHS,
    PRECISION_WHOLE,
    UnitOfTemperature,
)
from .entity import LocalTuyaEntity, async_setup_entry
from .core.dp_wrappers import RawDPWrapper, dp_wrapper_by_id
from .core.dp_wrapper_decorators import ClimateTempWrapper, DictSelectorWrapper
from .core.definitions import get_water_heater_definition
from .const import (
    CONF_TARGET_TEMPERATURE_DP,
    CONF_CURRENT_TEMPERATURE_DP,
    CONF_MIN_TEMP,
    CONF_MAX_TEMP,
    CONF_PRECISION,
    CONF_TARGET_PRECISION,
    CONF_MODE_DP,
    CONF_MODES,
    CONF_TARGET_TEMPERATURE_LOW_DP,
    CONF_TARGET_TEMPERATURE_HIGH_DP,
    DictSelector,
)

_LOGGER = logging.getLogger(__name__)


TEMPERATURE_CELSIUS = "celsius"
TEMPERATURE_FAHRENHEIT = "fahrenheit"

DEFAULT_TEMPERATURE_UNIT = TEMPERATURE_CELSIUS
DEFAULT_PRECISION = PRECISION_TENTHS
DEFAULT_TEMPERATURE_STEP = PRECISION_HALVES
PERCISION_SET = [PRECISION_WHOLE, PRECISION_HALVES, PRECISION_TENTHS]

OFF_MODE = "Off"


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(CONF_TARGET_TEMPERATURE_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_TARGET_TEMPERATURE_LOW_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_TARGET_TEMPERATURE_HIGH_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_CURRENT_TEMPERATURE_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_MIN_TEMP, default=DEFAULT_MIN_TEMP): vol.Coerce(float),
        vol.Optional(CONF_MAX_TEMP, default=DEFAULT_MAX_TEMP): vol.Coerce(float),
        vol.Optional(CONF_PRECISION, default=str(DEFAULT_PRECISION)): col_to_select(
            PERCISION_SET
        ),
        vol.Optional(
            CONF_TARGET_PRECISION, default=str(DEFAULT_PRECISION)
        ): col_to_select(PERCISION_SET),
        vol.Optional(CONF_MODE_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_MODES, default={}): ObjectSelector(),
        vol.Optional(CONF_TEMPERATURE_UNIT): col_to_select(
            [TEMPERATURE_CELSIUS, TEMPERATURE_FAHRENHEIT]
        ),
    }


def config_unit(unit):
    if unit == TEMPERATURE_FAHRENHEIT:
        return UnitOfTemperature.FAHRENHEIT
    else:
        return UnitOfTemperature.CELSIUS


class LocalTuyaWaterHeater(LocalTuyaEntity, WaterHeaterEntity):
    """Tuya WaterHeater device."""

    _enable_turn_on_off_backwards_compatibility = False

    def __init__(
        self,
        device,
        config_entry,
        switchid,
        description=None,
        **kwargs,
    ):
        """Initialize a new LocalTuyaWaterHeater."""
        super().__init__(device, config_entry, switchid, _LOGGER, **kwargs)
        self._available_modes = DictSelector(self._config.get(CONF_MODES, {}))

        self._precision = float(self._config.get(CONF_PRECISION, DEFAULT_PRECISION))
        self._precision_target = float(
            self._config.get(CONF_TARGET_PRECISION, DEFAULT_PRECISION)
        )

        if description is not None:
            definition = get_water_heater_definition(device, description)
            self._switch_wrapper = (
                definition.switch_wrapper if definition is not None else None
            )
            target_inner = (
                definition.target_temp_wrapper
                if definition is not None
                else None
            )
            current_inner = (
                definition.current_temp_wrapper
                if definition is not None
                else None
            )
            low_inner = (
                definition.target_low_wrapper
                if definition is not None
                else None
            )
            high_inner = (
                definition.target_high_wrapper
                if definition is not None
                else None
            )
            mode_inner = (
                definition.mode_wrapper if definition is not None else None
            )
        else:
            # Cloud spec wrappers for the configured DPs (core parity); DPs
            # with no cloud spec fall back to a raw wrapper.
            self._switch_wrapper = dp_wrapper_by_id(
                device, self._dp_id
            ) or RawDPWrapper(self._dp_id)

            target_dp = self._config.get(CONF_TARGET_TEMPERATURE_DP)
            target_inner = (
                dp_wrapper_by_id(device, target_dp) or RawDPWrapper(target_dp)
            ) if self.has_config(CONF_TARGET_TEMPERATURE_DP) else None

            current_dp = self._config.get(CONF_CURRENT_TEMPERATURE_DP)
            current_inner = (
                dp_wrapper_by_id(device, current_dp) or RawDPWrapper(current_dp)
            ) if self.has_config(CONF_CURRENT_TEMPERATURE_DP) else None

            low_dp = self._config.get(CONF_TARGET_TEMPERATURE_LOW_DP)
            low_inner = (
                dp_wrapper_by_id(device, low_dp) or RawDPWrapper(low_dp)
            ) if self.has_config(CONF_TARGET_TEMPERATURE_LOW_DP) else None

            high_dp = self._config.get(CONF_TARGET_TEMPERATURE_HIGH_DP)
            high_inner = (
                dp_wrapper_by_id(device, high_dp) or RawDPWrapper(high_dp)
            ) if self.has_config(CONF_TARGET_TEMPERATURE_HIGH_DP) else None

            mode_dp = self._config.get(CONF_MODE_DP)
            mode_inner = (
                dp_wrapper_by_id(device, mode_dp) or RawDPWrapper(mode_dp)
            ) if self.has_config(CONF_MODE_DP) else None

        self._target_temp_wrapper = (
            ClimateTempWrapper(target_inner, precision=self._precision_target)
            if target_inner is not None
            else None
        )
        self._current_temp_wrapper = (
            ClimateTempWrapper(current_inner, precision=self._precision)
            if current_inner is not None
            else None
        )
        self._target_low_wrapper = low_inner
        self._target_high_wrapper = high_inner
        self._mode_wrapper = (
            DictSelectorWrapper(mode_inner, self._available_modes)
            if mode_inner is not None
            else None
        )

    @property
    def supported_features(self):
        """Flag supported features."""
        supported_features = WaterHeaterEntityFeature(0)
        if self._target_temp_wrapper is not None:
            supported_features |= WaterHeaterEntityFeature.TARGET_TEMPERATURE
        if self._mode_wrapper is not None:
            supported_features |= WaterHeaterEntityFeature.OPERATION_MODE

        supported_features |= WaterHeaterEntityFeature.ON_OFF

        return supported_features

    @property
    def precision(self):
        """Return the precision of the system."""
        return self._precision

    @property
    def temperature_unit(self):
        """Return the unit of measurement used by the platform."""
        return config_unit(self._config.get(CONF_TEMPERATURE_UNIT))

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return self._config.get(CONF_MIN_TEMP, DEFAULT_MIN_TEMP)

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return self._config.get(CONF_MAX_TEMP, DEFAULT_MAX_TEMP)

    @property
    def operation_list(self) -> list[str] | None:
        """Return the list of available operation modes."""
        return self._available_modes.names + [OFF_MODE]

    @property
    def current_operation(self):
        """Return the current operation mode."""
        if not self._read_wrapper(self._switch_wrapper):
            return OFF_MODE
        if self._mode_wrapper is not None:
            return self._read_wrapper(self._mode_wrapper)
        return None

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._read_wrapper(self._current_temp_wrapper)

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._read_wrapper(self._target_temp_wrapper)

    @property
    def target_temperature_high(self) -> float | None:
        """Return the highbound target temperature we try to reach."""
        return self._read_wrapper(self._target_high_wrapper)

    @property
    def target_temperature_low(self) -> float | None:
        """Return the lowbound target temperature we try to reach."""
        return self._read_wrapper(self._target_low_wrapper)

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        if ATTR_TEMPERATURE in kwargs and self._target_temp_wrapper is not None:
            await self._async_send_wrapper_updates(
                self._target_temp_wrapper, kwargs[ATTR_TEMPERATURE]
            )

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        """Set new target operation mode."""
        if operation_mode == OFF_MODE:
            return await self.async_turn_off()
        if not self._read_wrapper(self._switch_wrapper):
            await self._async_send_wrapper_updates(self._switch_wrapper, True)
        await self._async_send_wrapper_updates(self._mode_wrapper, operation_mode)

    async def async_turn_on(self) -> None:
        """Turn the entity on."""
        await self._async_send_wrapper_updates(self._switch_wrapper, True)

    async def async_turn_off(self) -> None:
        """Turn the entity off."""
        await self._async_send_wrapper_updates(self._switch_wrapper, False)


async_setup_entry = partial(
    async_setup_entry, DOMAIN, LocalTuyaWaterHeater, flow_schema
)
