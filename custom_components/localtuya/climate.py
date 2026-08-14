"""Platform to locally control Tuya-based climate devices."""

import asyncio
from enum import StrEnum
import logging
from functools import partial
from .config_flow import col_to_select
from homeassistant.helpers.selector import ObjectSelector

import voluptuous as vol
from homeassistant.components.climate import (
    DEFAULT_MAX_TEMP,
    DEFAULT_MIN_TEMP,
    DOMAIN,
    ClimateEntity,
)
from homeassistant.components.climate.const import (
    HVACMode,
    HVACAction,
    PRESET_AWAY,
    PRESET_ECO,
    PRESET_HOME,
    PRESET_NONE,
    ClimateEntityFeature,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_TEMPERATURE_UNIT,
    PRECISION_HALVES,
    PRECISION_TENTHS,
    PRECISION_WHOLE,
    UnitOfTemperature,
)
from homeassistant.util.unit_system import US_CUSTOMARY_SYSTEM
from .entity import LocalTuyaEntity, async_setup_entry
from .core.dp_wrappers import RawDPWrapper, dp_wrapper_by_id
from .core.dp_wrapper_decorators import (
    ClimateTempWrapper,
    DictSelectorWrapper,
    HumidityCoefficientWrapper,
)
from .core.definitions import get_climate_definition
from .const import (
    CONF_CURRENT_HUMIDITY_DP,
    CONF_CURRENT_TEMPERATURE_DP,
    CONF_ECO_DP,
    CONF_ECO_VALUE,
    CONF_HEURISTIC_ACTION,
    CONF_HUMIDITY_COEFFICIENT,
    CONF_HVAC_ACTION_DP,
    CONF_HVAC_ACTION_SET,
    CONF_HVAC_ADD_OFF,
    CONF_HVAC_MODE_DP,
    CONF_HVAC_MODE_SET,
    CONF_HVAC_SWITCH_DP,
    CONF_PRECISION,
    CONF_PRESET_DP,
    CONF_PRESET_SET,
    CONF_TARGET_HUMIDITY_DP,
    CONF_TARGET_PRECISION,
    CONF_TARGET_TEMPERATURE_DP,
    CONF_TEMPERATURE_STEP,
    CONF_MIN_TEMP,
    CONF_MAX_TEMP,
    CONF_FAN_SPEED_DP,
    CONF_FAN_SPEED_LIST,
    CONF_SWING_MODE_DP,
    CONF_SWING_MODES,
    CONF_SWING_HORIZONTAL_DP,
    CONF_SWING_HORIZONTAL_MODES,
    DictSelector,
)

_LOGGER = logging.getLogger(__name__)


HVAC_OFF = {HVACMode.OFF.value: "off"}  # Migrate to 3
RENAME_HVAC_MODE_SETS = {  # Migrate to 3
    ("manual", "Manual", "hot", "m", "True"): HVACMode.HEAT.value,
    ("auto", "0", "p", "Program"): HVACMode.AUTO.value,
    ("freeze", "cold", "1"): HVACMode.COOL.value,
    ("wet"): HVACMode.DRY.value,
}
RENAME_ACTION_SETS = {  # Migrate to 3
    ("open", "opened", "heating", "Heat", "True"): HVACAction.HEATING.value,
    ("closed", "close", "no_heating"): HVACAction.IDLE.value,
    ("Warming", "warming", "False"): HVACAction.IDLE.value,
    ("cooling"): HVACAction.COOLING.value,
    ("off"): HVACAction.OFF.value,
}
RENAME_PRESET_SETS = {  # Migrate to 3
    "Holiday": (PRESET_AWAY),
    "Program": (PRESET_HOME),
    "Manual": (PRESET_NONE, "manual"),
    "Auto": "auto",
    "Manual": "manual",
    "Smart": "smart",
    "Comfort": "comfortable",
    "ECO": "eco",
}


HVAC_MODE_SETS = {
    HVACMode.OFF: False,
    HVACMode.AUTO: "auto",
    HVACMode.COOL: "cold",
    HVACMode.HEAT: "hot",
    HVACMode.HEAT_COOL: "heat",
    HVACMode.DRY: "wet",
    HVACMode.FAN_ONLY: "wind",
}

HVAC_ACTION_SETS = {
    HVACAction.HEATING: "opened",
    HVACAction.IDLE: "closed",
}


class SupportedTemps(StrEnum):
    C = "celsius"
    F = "fahrenheit"
    C_F = f"celsius/fahrenheit"
    F_C = f"fahrenheit/celsius"


SUPPORTED_TEMPERATURES = {
    UnitOfTemperature.CELSIUS: SupportedTemps.C,
    UnitOfTemperature.FAHRENHEIT: SupportedTemps.F,
    f"Target Temperature: {UnitOfTemperature.CELSIUS} | Current Temperature {UnitOfTemperature.FAHRENHEIT}": SupportedTemps.C_F,
    f"Current Temperature {UnitOfTemperature.CELSIUS} | Target Temperature: {UnitOfTemperature.FAHRENHEIT} ": SupportedTemps.F_C,
}
SUPPORTED_PRECISIONS = [0.01, PRECISION_TENTHS, PRECISION_HALVES, PRECISION_WHOLE]

DEFAULT_TEMPERATURE_UNIT = SupportedTemps.C
DEFAULT_PRECISION = PRECISION_TENTHS
DEFAULT_TEMPERATURE_STEP = PRECISION_HALVES
# Empirically tested to work for AVATTO thermostat
MODE_WAIT = 0.1

FAN_SPEEDS_DEFAULT = {"1": "Low", "2": "Medium", "3": "High"}


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(CONF_TARGET_TEMPERATURE_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_CURRENT_TEMPERATURE_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_TEMPERATURE_STEP): col_to_select(
            [PRECISION_WHOLE, PRECISION_HALVES, PRECISION_TENTHS]
        ),
        vol.Optional(CONF_MIN_TEMP, default=DEFAULT_MIN_TEMP): vol.Coerce(float),
        vol.Optional(CONF_MAX_TEMP, default=DEFAULT_MAX_TEMP): vol.Coerce(float),
        vol.Optional(CONF_PRECISION, default=str(DEFAULT_PRECISION)): col_to_select(
            SUPPORTED_PRECISIONS
        ),
        vol.Optional(
            CONF_TARGET_PRECISION, default=str(DEFAULT_PRECISION)
        ): col_to_select(SUPPORTED_PRECISIONS),
        vol.Optional(CONF_HVAC_MODE_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_HVAC_MODE_SET, default=HVAC_MODE_SETS): ObjectSelector(),
        vol.Optional(CONF_HVAC_SWITCH_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_HVAC_ACTION_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_HVAC_ACTION_SET, default=HVAC_ACTION_SETS): ObjectSelector(),
        vol.Optional(CONF_CURRENT_HUMIDITY_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_TARGET_HUMIDITY_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_HUMIDITY_COEFFICIENT, default=1.0): vol.Coerce(float),
        vol.Optional(CONF_ECO_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_ECO_VALUE): str,
        vol.Optional(CONF_PRESET_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_PRESET_SET, default={}): ObjectSelector(),
        vol.Optional(CONF_SWING_MODE_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_SWING_MODES, default={}): ObjectSelector(),
        vol.Optional(CONF_SWING_HORIZONTAL_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_SWING_HORIZONTAL_MODES, default={}): ObjectSelector(),
        vol.Optional(CONF_FAN_SPEED_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_FAN_SPEED_LIST, default=FAN_SPEEDS_DEFAULT): ObjectSelector(),
        vol.Optional(CONF_TEMPERATURE_UNIT): col_to_select(SUPPORTED_TEMPERATURES),
        vol.Optional(CONF_HEURISTIC_ACTION): bool,
    }


# Converters
def f_to_c(num):
    return (num - 32) * 5 / 9 if num else num


def c_to_f(num):
    return (num * 1.8) + 32 if num else num


def config_unit(unit):
    if unit == SupportedTemps.F:
        return UnitOfTemperature.FAHRENHEIT
    else:
        return UnitOfTemperature.CELSIUS


class LocalTuyaClimate(LocalTuyaEntity, ClimateEntity):
    """Tuya climate device."""

    _enable_turn_on_off_backwards_compatibility = False

    def __init__(
        self,
        device,
        config_entry,
        switchid,
        description=None,
        **kwargs,
    ):
        """Initialize a new LocalTuyaClimate."""
        super().__init__(device, config_entry, switchid, _LOGGER, **kwargs)
        self._state = None
        self._state_on, self._state_off = True, False
        self._target_temp_forced_to_celsius = None
        self._precision = float(self._config.get(CONF_PRECISION, DEFAULT_PRECISION))
        self._precision_target = float(
            self._config.get(CONF_TARGET_PRECISION, DEFAULT_PRECISION)
        )
        self._humidity_coefficient = float(
            self._config.get(CONF_HUMIDITY_COEFFICIENT, 1.0)
        )
        self._hvac_switch_dp = self._config.get(CONF_HVAC_SWITCH_DP)

        # HVAC Modes
        self._hvac_mode_dp = self._config.get(CONF_HVAC_MODE_DP)
        hvac_modes = self._config.get(CONF_HVAC_MODE_SET, {}) or {}
        if hvac_modes:
            # HA HVAC Modes are all lower case.
            hvac_modes = {k.lower(): v for k, v in hvac_modes.copy().items()}

        self._preset_dp = self._config.get(CONF_PRESET_DP)
        preset_set: dict = self._config.get(CONF_PRESET_SET, {}) or {}
        # Sort Modes If the HVAC isn't supported by HA then we add it as preset.
        if self._preset_dp == self._hvac_mode_dp or not self._preset_dp:
            for k in hvac_modes.copy().keys():
                if k not in HVACMode:
                    self._preset_dp = self._hvac_mode_dp
                    preset_set[k] = hvac_modes.pop(k)

        self._preset_set = DictSelector(preset_set)
        self._hvac_mode_set = DictSelector(hvac_modes, reverse=True)

        # HVAC Actions
        self._hvac_action_dp = self._config.get(CONF_HVAC_ACTION_DP)
        actions_set = self._config.get(CONF_HVAC_ACTION_SET, {}) or {}
        if actions_set:
            actions_set = {k.lower(): v for k, v in actions_set.copy().items()}
        self._hvac_action_set = DictSelector(actions_set, reverse=True)

        # Fan
        self._fan_speed_dp = self._config.get(CONF_FAN_SPEED_DP)
        self._fan_speeds = DictSelector(self._config.get(CONF_FAN_SPEED_LIST, {}))

        # Swing configurations.
        self._swing_v_mode_dp = self._config.get(CONF_SWING_MODE_DP)
        self._swing_v_modes = DictSelector(self._config.get(CONF_SWING_MODES, {}))
        self._swing_h_mode_dp = self._config.get(CONF_SWING_HORIZONTAL_DP)
        self._swing_h_modes = DictSelector(
            self._config.get(CONF_SWING_HORIZONTAL_MODES, {})
        )

        # Eco!?
        self._eco_dp = self._config.get(CONF_ECO_DP)
        self._eco_value = self._config.get(CONF_ECO_VALUE, "ECO")
        self._has_presets = self._eco_dp or (self._preset_dp and self._preset_set)

        self._min_temp = self._config.get(CONF_MIN_TEMP, DEFAULT_MIN_TEMP)
        self._max_temp = self._config.get(CONF_MAX_TEMP, DEFAULT_MAX_TEMP)

        # Temperature unit
        config_temp_unit = self._config.get(CONF_TEMPERATURE_UNIT, "")
        target_unit, *current_unit = config_temp_unit.split("/")
        set_temp_unit = UnitOfTemperature.CELSIUS
        if current_unit:
            self._target_temp_forced_to_celsius = target_unit == SupportedTemps.F
            if self._target_temp_forced_to_celsius:
                self._min_temp = f_to_c(self._min_temp)
                self._max_temp = f_to_c(self._max_temp)
        else:
            set_temp_unit = config_unit(config_temp_unit)
        self._temperature_unit = set_temp_unit

        # Conversion wrappers (core parity): the entity stays thin and all
        # temperature/humidity/mode conversion lives in the decorators.
        target_unit_from = f_to_c if self._target_temp_forced_to_celsius is True else None
        target_unit_to = c_to_f if self._target_temp_forced_to_celsius is True else None
        current_unit_from = f_to_c if self._target_temp_forced_to_celsius is False else None

        if description is not None:
            # Definition-driven: resolve the DP wrappers by dpcode. Humidity,
            # swing and eco DPs are not in the category tables, so they stay
            # None for the auto-configured path.
            definition = get_climate_definition(device, description)
            switch_inner = (
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
            hvac_mode_inner = (
                definition.hvac_mode_wrapper if definition is not None else None
            )
            hvac_action_inner = (
                definition.hvac_action_wrapper
                if definition is not None
                else None
            )
            preset_inner = (
                definition.preset_wrapper if definition is not None else None
            )
            fan_speed_inner = (
                definition.fan_speed_wrapper if definition is not None else None
            )
            current_humidity_inner = None
            target_humidity_inner = None
            swing_v_inner = None
            swing_h_inner = None
        else:
            # Manual config-driven path: resolve by dp_id with raw fallback.
            switch_inner = dp_wrapper_by_id(
                device, self._hvac_switch_dp or self._dp_id
            ) or RawDPWrapper(self._hvac_switch_dp or self._dp_id)
            target_inner = self._resolve_inner(device, CONF_TARGET_TEMPERATURE_DP)
            current_inner = self._resolve_inner(device, CONF_CURRENT_TEMPERATURE_DP)
            hvac_mode_inner = self._resolve_inner(device, CONF_HVAC_MODE_DP)
            hvac_action_inner = self._resolve_inner(device, CONF_HVAC_ACTION_DP)
            preset_inner = self._resolve_inner(device, CONF_PRESET_DP)
            fan_speed_inner = self._resolve_inner(device, CONF_FAN_SPEED_DP)
            current_humidity_inner = self._resolve_inner(
                device, CONF_CURRENT_HUMIDITY_DP
            )
            target_humidity_inner = self._resolve_inner(
                device, CONF_TARGET_HUMIDITY_DP
            )
            swing_v_inner = self._resolve_inner(device, CONF_SWING_MODE_DP)
            swing_h_inner = self._resolve_inner(
                device, CONF_SWING_HORIZONTAL_DP
            )

        self._switch_wrapper = switch_inner
        self._target_temp_wrapper = self._temp_wrapper(
            target_inner, self._precision_target,
            unit_from=target_unit_from, unit_to=target_unit_to,
        )
        self._current_temp_wrapper = self._temp_wrapper(
            current_inner, self._precision, unit_from=current_unit_from,
        )
        self._current_humidity_wrapper = self._humidity_wrapper(
            current_humidity_inner
        )
        self._target_humidity_wrapper = self._humidity_wrapper(
            target_humidity_inner
        )
        self._hvac_mode_wrapper = self._selector_wrapper(
            hvac_mode_inner, self._hvac_mode_set
        )
        self._preset_wrapper = self._selector_wrapper(
            preset_inner, self._preset_set, default=PRESET_NONE
        )
        self._hvac_action_wrapper = self._selector_wrapper(
            hvac_action_inner, self._hvac_action_set
        )
        self._fan_speed_wrapper = self._selector_wrapper(
            fan_speed_inner, self._fan_speeds
        )
        self._swing_v_wrapper = self._selector_wrapper(
            swing_v_inner, self._swing_v_modes
        )
        self._swing_h_wrapper = self._selector_wrapper(
            swing_h_inner, self._swing_h_modes
        )

    def _resolve_inner(self, device, conf_key):
        """Resolve a configured DP's wrapper (raw fallback) for the manual path."""
        dp = self._config.get(conf_key)
        if not self.has_config(conf_key):
            return None
        return dp_wrapper_by_id(device, dp) or RawDPWrapper(dp)

    def _temp_wrapper(self, inner, precision, unit_from=None, unit_to=None):
        """Build a ClimateTempWrapper for a resolved temperature DP wrapper."""
        if inner is None:
            return None
        return ClimateTempWrapper(
            inner, precision=precision, unit_from=unit_from, unit_to=unit_to
        )

    def _humidity_wrapper(self, inner):
        """Build a HumidityCoefficientWrapper for a resolved humidity DP wrapper."""
        if inner is None:
            return None
        return HumidityCoefficientWrapper(
            inner, coefficient=self._humidity_coefficient
        )

    def _selector_wrapper(self, inner, selector, default=None):
        """Build a DictSelectorWrapper for a resolved enum DP wrapper."""
        if inner is None:
            return None
        return DictSelectorWrapper(inner, selector, default=default)

    @property
    def _is_on(self):
        """Return if the device is on."""
        state = self._read_wrapper(self._switch_wrapper)
        if isinstance(state, bool):
            return state
        if self._hvac_switch_dp:
            return self.dp_value(self._hvac_switch_dp) == self._state_on
        return self._state and self._state != self._state_off

    @property
    def supported_features(self):
        """Flag supported features."""
        supported_features = ClimateEntityFeature(0)
        if self.has_config(CONF_TARGET_TEMPERATURE_DP):
            supported_features |= ClimateEntityFeature.TARGET_TEMPERATURE
        if self.has_config(CONF_TARGET_HUMIDITY_DP):
            supported_features |= ClimateEntityFeature.TARGET_HUMIDITY
        if self._has_presets:
            supported_features |= ClimateEntityFeature.PRESET_MODE
        if self._fan_speed_dp and self._fan_speeds:
            supported_features |= ClimateEntityFeature.FAN_MODE
        if self._swing_v_mode_dp and self._swing_v_modes:
            supported_features |= ClimateEntityFeature.SWING_MODE
        if self._swing_h_mode_dp and self._swing_h_modes:
            supported_features |= ClimateEntityFeature.SWING_HORIZONTAL_MODE

        supported_features |= ClimateEntityFeature.TURN_OFF
        supported_features |= ClimateEntityFeature.TURN_ON

        return supported_features

    @property
    def precision(self):
        """Return the precision of the system."""
        return self._precision

    @property
    def temperature_unit(self):
        """Return the unit of measurement used by the platform."""
        return self._temperature_unit

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        # DEFAULT_MIN_TEMP is in C
        return self._min_temp

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        # DEFAULT_MAX_TEMP is in C
        return self._max_temp

    async def async_set_hvac_mode(self, hvac_mode: HVACMode):
        """Set new target hvac mode."""
        commands = []
        if not self._is_on:
            commands.extend(
                self._switch_wrapper.get_update_commands(
                    self._device, self._state_on
                )
            )
        if hvac_mode in self._hvac_mode_set.names and self._hvac_mode_wrapper:
            commands.extend(
                self._hvac_mode_wrapper.get_update_commands(
                    self._device, hvac_mode
                )
            )
        elif hvac_mode == HVACMode.OFF:
            commands.extend(
                self._switch_wrapper.get_update_commands(
                    self._device, self._state_off
                )
            )
        await self._async_send_commands(commands)

    async def async_set_preset_mode(self, preset_mode):
        """Set new target preset mode."""
        if preset_mode == PRESET_ECO:
            await self._device.set_dp(self._eco_value, self._eco_dp)
            return

        await self._async_send_wrapper_updates(self._preset_wrapper, preset_mode)

    async def async_set_fan_mode(self, fan_mode):
        """Set new target fan mode."""
        if not self._is_on:
            await self._async_send_wrapper_updates(self._switch_wrapper, self._state_on)

        await self._async_send_wrapper_updates(self._fan_speed_wrapper, fan_mode)

    async def async_set_humidity(self, humidity):
        """Set new target humidity."""
        if self._target_humidity_wrapper is not None:
            await self._async_send_wrapper_updates(
                self._target_humidity_wrapper, humidity
            )

    async def async_set_swing_mode(self, swing_mode):
        """Set new target swing operation."""
        await self._async_send_wrapper_updates(self._swing_v_wrapper, swing_mode)

    async def async_set_swing_horizontal_mode(self, swing_mode):
        """Set new target horizontal swing operation."""
        await self._async_send_wrapper_updates(self._swing_h_wrapper, swing_mode)

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        if ATTR_TEMPERATURE in kwargs and self._target_temp_wrapper is not None:
            await self._async_send_wrapper_updates(
                self._target_temp_wrapper, kwargs[ATTR_TEMPERATURE]
            )

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._read_wrapper(self._current_temp_wrapper)

    @property
    def current_humidity(self):
        """Return the current humidity."""
        return self._read_wrapper(self._current_humidity_wrapper)

    @property
    def target_temperature(self):
        """Return the temperature currently set to be reached."""
        return self._read_wrapper(self._target_temp_wrapper)

    @property
    def target_humidity(self):
        """Return the humidity currently set to be reached."""
        return self._read_wrapper(self._target_humidity_wrapper)

    @property
    def min_humidity(self):
        """Return the minimum humidity."""
        return 0

    @property
    def max_humidity(self):
        """Return the maximum humidity."""
        return 100

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        target_step = self._config.get(CONF_TEMPERATURE_STEP, DEFAULT_TEMPERATURE_STEP)
        return float(target_step)

    @property
    def hvac_mode(self):
        """Return hvac mode."""
        if not self._is_on:
            return HVACMode.OFF
        if self._hvac_mode_wrapper is None:
            return HVACMode.HEAT

        return self._read_wrapper(self._hvac_mode_wrapper)

    @property
    def hvac_modes(self):
        """Return the list of available operation modes."""
        if not self.has_config(CONF_HVAC_MODE_DP):
            return [HVACMode.OFF]

        modes = self._hvac_mode_set.names
        if self._config.get(CONF_HVAC_ADD_OFF, True) and HVACMode.OFF not in modes:
            modes.append(HVACMode.OFF)
        return modes

    @property
    def hvac_action(self):
        """Return the current running hvac operation if supported."""
        if not self._is_on:
            return HVACAction.OFF

        hvac_action = self._read_wrapper(self._hvac_action_wrapper)
        hvac_mode = self.hvac_mode

        if (
            (self._config.get(CONF_HEURISTIC_ACTION) or not self._hvac_action_dp)
            and (target_temperature := self.target_temperature) is not None
            and (current_temperature := self.current_temperature) is not None
        ):
            # This function assumes that action changes based on target step different from current.
            target_step = self.target_temperature_step
            is_heating = current_temperature < (target_temperature - target_step)
            is_cooling = current_temperature > (target_temperature + target_step)

            if hvac_mode == HVACMode.HEAT:
                if is_heating:
                    hvac_action = HVACAction.HEATING
                elif current_temperature >= target_temperature:
                    hvac_action = HVACAction.IDLE
            elif hvac_mode == HVACMode.COOL:
                if is_cooling:
                    hvac_action = HVACAction.COOLING
                elif current_temperature <= target_temperature:
                    hvac_action = HVACAction.IDLE
            elif hvac_mode == HVACMode.HEAT_COOL:
                if is_heating:
                    hvac_action = HVACAction.HEATING
                elif is_cooling:
                    hvac_action = HVACAction.COOLING
                elif current_temperature == target_temperature:
                    hvac_action = HVACAction.IDLE
            elif hvac_mode == HVACMode.DRY:
                hvac_action = HVACAction.DRYING
            elif hvac_mode == HVACMode.FAN_ONLY:
                hvac_action = HVACAction.FAN

        return hvac_action

    @property
    def preset_mode(self):
        """Return preset mode."""
        mode = self.dp_value(CONF_HVAC_MODE_DP)
        if self._preset_dp == self._hvac_mode_dp and (
            mode in self._hvac_mode_set.values
        ):
            return None

        if self._eco_dp and self.dp_value(CONF_ECO_DP) == self._eco_value:
            return PRESET_ECO

        return self._read_wrapper(self._preset_wrapper)

    @property
    def preset_modes(self):
        """Return the list of available presets modes."""
        if not self._has_presets:
            return None

        presets = self._preset_set.names
        if self._eco_dp:
            presets.append(PRESET_ECO)
        return presets

    @property
    def fan_mode(self):
        """Return fan mode."""
        return self._read_wrapper(self._fan_speed_wrapper)

    @property
    def fan_modes(self) -> list:
        """Return the list of available fan modes."""
        return self._fan_speeds.names

    @property
    def swing_mode(self) -> str | None:
        """Return swing mode."""
        return self._read_wrapper(self._swing_v_wrapper)

    @property
    def swing_modes(self) -> list[str] | None:
        """Return the list of available swing modes."""
        return self._swing_v_modes.names

    @property
    def swing_horizontal_mode(self) -> str | None:
        """Return the horizontal swing setting."""
        return self._read_wrapper(self._swing_h_wrapper)

    @property
    def swing_horizontal_modes(self) -> list[str] | None:
        """Return the list of available horizontal swing modes."""
        return self._swing_h_modes.names

    async def async_turn_on(self) -> None:
        """Turn the device on, retaining current HVAC (if supported)."""
        await self._async_send_wrapper_updates(self._switch_wrapper, True)

    async def async_turn_off(self) -> None:
        """Turn the device off, retaining current HVAC (if supported)."""
        await self._async_send_wrapper_updates(self._switch_wrapper, False)

    def connection_made(self):
        """The connection has made with the device and status retrieved. configure entity based on it."""
        super().connection_made()

        match self.dp_value(self._dp_id):
            case str() as v if v.lower() in ("on", "off"):
                self._state_on = "ON" if v.isupper() else "on"
                self._state_off = "OFF" if v.isupper() else "off"
            case int() as v if not isinstance(v, bool) and v in (0, 1):
                self._state_on = 1
                self._state_off = 0


async_setup_entry = partial(async_setup_entry, DOMAIN, LocalTuyaClimate, flow_schema)
