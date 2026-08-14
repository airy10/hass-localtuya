"""Resolved per-platform wrapper definitions (core's ``get_default_definition``).

Core tuya resolves each entity's wrappers *by dpcode* from a
``DeviceCategory -> EntityDescription`` table, gated on the primary DP being
present in the device spec. This module is the localtuya equivalent: given a
device (exposing the core-compatible ``function``/``status_range``/``status``
surface) and a ``LocalTuyaEntity`` description, it resolves the wrappers by
dpcode and applies the relevant conversion decorators from
``core/dp_wrapper_decorators.py``.

This is the runtime half of SPEC_DEFINITION_DRIVEN_RUNTIME.md. Light and
switch were implemented first (Phases 1-2); the remaining platforms were
added in Phases 3-5.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from ..const import (
    CONF_BRIGHTNESS_LOWER,
    CONF_BRIGHTNESS_UPPER,
    CONF_COLOR_TEMP_MAX_KELVIN,
    CONF_COLOR_TEMP_MIN_KELVIN,
    CONF_COLOR_TEMP_REVERSE,
)
from .dp_wrappers import DPCodeWrapper, dp_wrapper_by_code
from .dp_wrapper_decorators import (
    BrightnessWrapper,
    ColorTempWrapper,
    ColorTypeData,
    StringColorWrapper,
)

__all__ = [
    "AlarmControlPanelDefinition",
    "CoverDefinition",
    "ClimateDefinition",
    "DPCodeDefinition",
    "FanDefinition",
    "HumidifierDefinition",
    "LightDefinition",
    "NumberDefinition",
    "SelectDefinition",
    "SwitchDefinition",
    "VacuumDefinition",
    "WaterHeaterDefinition",
    "get_alarm_control_panel_definition",
    "get_binary_sensor_definition",
    "get_button_definition",
    "get_climate_definition",
    "get_cover_definition",
    "get_fan_definition",
    "get_humidifier_definition",
    "get_light_definition",
    "get_lock_definition",
    "get_number_definition",
    "get_remote_definition",
    "get_select_definition",
    "get_sensor_definition",
    "get_siren_definition",
    "get_switch_definition",
    "get_vacuum_definition",
    "get_valve_definition",
    "get_water_heater_definition",
    "resolve",
]

# ``localtuya_light()`` defaults (core/ha_entities/lights.py); fallback for
# descriptions whose custom configs omit them.
DEFAULT_LIGHT_BRIGHTNESS_LOWER = 29
DEFAULT_LIGHT_BRIGHTNESS_UPPER = 1000
DEFAULT_LIGHT_MIN_KELVIN = 2700
DEFAULT_LIGHT_MAX_KELVIN = 6500


def resolve(
    device: Any,
    dpcode: str | tuple[str, ...] | None,
    decorator: Callable[..., DPCodeWrapper] | None = None,
    **decorator_kwargs: Any,
) -> DPCodeWrapper | None:
    """Resolve a wrapper for a dpcode (or the first tuple alternative present).

    Returns None when the dpcode is absent from the device spec (core's spec
    gate). When ``decorator`` is given the resolved wrapper is wrapped with it,
    forwarding ``decorator_kwargs``.
    """
    if dpcode is None:
        return None
    codes = dpcode if isinstance(dpcode, tuple) else (dpcode,)
    wrapper: DPCodeWrapper | None = None
    for code in codes:
        if wrapper := dp_wrapper_by_code(device, code):
            break
    if wrapper is None:
        return None
    if decorator is not None:
        wrapper = decorator(wrapper, **decorator_kwargs)
    return wrapper


def _config_value(configs: dict | None, key: str, default: Any) -> Any:
    """Return a resolved value from a description's custom configs.

    Handles ``CLOUD_VALUE`` placeholders (which carry a ``default_value`` until
    cloud-resolved) and missing/None entries.
    """
    if not configs:
        return default
    value = configs.get(key, default)
    if value is None:
        return default
    if hasattr(value, "default_value"):
        return value.default_value
    return value


@dataclass
class SwitchDefinition:
    """Resolved wrappers for a switch entity."""

    switch_wrapper: DPCodeWrapper | None


def get_switch_definition(device: Any, description: Any) -> SwitchDefinition | None:
    """Resolve the switch wrapper for a description; None if the DP is absent."""
    conf = getattr(description, "localtuya_conf", {}) or {}
    switch = resolve(device, conf.get("id"))
    if switch is None:
        return None
    return SwitchDefinition(switch_wrapper=switch)


@dataclass
class LightDefinition:
    """Resolved wrappers for a light entity (mirrors core LightDefinition)."""

    switch_wrapper: DPCodeWrapper | None
    brightness_wrapper: DPCodeWrapper | None
    color_data_wrapper: DPCodeWrapper | None
    color_mode_wrapper: DPCodeWrapper | None
    color_temp_wrapper: DPCodeWrapper | None


def get_light_definition(device: Any, description: Any) -> LightDefinition | None:
    """Resolve the light wrappers for a description; None if the switch DP is absent."""
    conf = getattr(description, "localtuya_conf", {}) or {}
    configs = getattr(description, "entity_configs", {}) or {}

    switch = resolve(device, conf.get("id"))
    if switch is None:
        return None

    lower = int(_config_value(configs, CONF_BRIGHTNESS_LOWER, DEFAULT_LIGHT_BRIGHTNESS_LOWER))
    upper = int(_config_value(configs, CONF_BRIGHTNESS_UPPER, DEFAULT_LIGHT_BRIGHTNESS_UPPER))
    min_kelvin = int(_config_value(configs, CONF_COLOR_TEMP_MIN_KELVIN, DEFAULT_LIGHT_MIN_KELVIN))
    max_kelvin = int(_config_value(configs, CONF_COLOR_TEMP_MAX_KELVIN, DEFAULT_LIGHT_MAX_KELVIN))
    reverse = bool(_config_value(configs, CONF_COLOR_TEMP_REVERSE, False))

    color_type_data = ColorTypeData.from_config(getattr(device, "color_data_spec", None))

    return LightDefinition(
        switch_wrapper=switch,
        brightness_wrapper=resolve(
            device,
            conf.get("brightness"),
            BrightnessWrapper,
            lower=lower,
            upper=upper,
        ),
        color_data_wrapper=resolve(
            device,
            conf.get("color"),
            StringColorWrapper,
            color_type_data=color_type_data,
            lower_brightness=lower,
            upper_brightness=upper,
        ),
        color_mode_wrapper=resolve(device, conf.get("color_mode")),
        color_temp_wrapper=resolve(
            device,
            conf.get("color_temp"),
            ColorTempWrapper,
            min_kelvin=min_kelvin,
            max_kelvin=max_kelvin,
            lower=lower,
            upper=upper,
            reverse=reverse,
        ),
    )


@dataclass
class FanDefinition:
    """Resolved wrappers for a fan entity."""

    switch_wrapper: DPCodeWrapper | None
    speed_wrapper: DPCodeWrapper | None
    oscillate_wrapper: DPCodeWrapper | None
    direction_wrapper: DPCodeWrapper | None


def get_fan_definition(device: Any, description: Any) -> FanDefinition | None:
    """Resolve the fan wrappers; None if the switch DP is absent."""
    conf = getattr(description, "localtuya_conf", {}) or {}
    if (switch := resolve(device, conf.get("id"))) is None:
        return None
    return FanDefinition(
        switch_wrapper=switch,
        speed_wrapper=resolve(device, conf.get("fan_speed_control")),
        oscillate_wrapper=resolve(device, conf.get("fan_oscillating_control")),
        direction_wrapper=resolve(device, conf.get("fan_direction")),
    )


@dataclass
class CoverDefinition:
    """Resolved wrappers for a cover entity."""

    set_position_wrapper: DPCodeWrapper | None


def get_cover_definition(device: Any, description: Any) -> CoverDefinition:
    """Resolve the cover set-position wrapper (the primary DP stays raw)."""
    conf = getattr(description, "localtuya_conf", {}) or {}
    return CoverDefinition(
        set_position_wrapper=resolve(device, conf.get("set_position_dp")),
    )


@dataclass
class ClimateDefinition:
    """Resolved wrappers for a climate entity."""

    switch_wrapper: DPCodeWrapper | None
    target_temp_wrapper: DPCodeWrapper | None
    current_temp_wrapper: DPCodeWrapper | None
    hvac_mode_wrapper: DPCodeWrapper | None
    hvac_action_wrapper: DPCodeWrapper | None
    preset_wrapper: DPCodeWrapper | None
    fan_speed_wrapper: DPCodeWrapper | None


def get_climate_definition(device: Any, description: Any) -> ClimateDefinition | None:
    """Resolve the climate wrappers; None if the switch DP is absent."""
    conf = getattr(description, "localtuya_conf", {}) or {}
    if (switch := resolve(device, conf.get("id"))) is None:
        return None
    return ClimateDefinition(
        switch_wrapper=switch,
        target_temp_wrapper=resolve(device, conf.get("target_temperature_dp")),
        current_temp_wrapper=resolve(device, conf.get("current_temperature_dp")),
        hvac_mode_wrapper=resolve(device, conf.get("hvac_mode_dp")),
        hvac_action_wrapper=resolve(device, conf.get("hvac_action_dp")),
        preset_wrapper=resolve(device, conf.get("preset_dp")),
        fan_speed_wrapper=resolve(device, conf.get("fan_speed_dp")),
    )


@dataclass
class HumidifierDefinition:
    """Resolved wrappers for a humidifier entity."""

    switch_wrapper: DPCodeWrapper | None
    mode_wrapper: DPCodeWrapper | None
    target_humidity_wrapper: DPCodeWrapper | None
    current_humidity_wrapper: DPCodeWrapper | None


def get_humidifier_definition(
    device: Any, description: Any
) -> HumidifierDefinition | None:
    """Resolve the humidifier wrappers; None if the switch DP is absent."""
    conf = getattr(description, "localtuya_conf", {}) or {}
    if (switch := resolve(device, conf.get("id"))) is None:
        return None
    return HumidifierDefinition(
        switch_wrapper=switch,
        mode_wrapper=resolve(device, conf.get("humidifier_mode_dp")),
        target_humidity_wrapper=resolve(
            device, conf.get("humidifier_set_humidity_dp")
        ),
        current_humidity_wrapper=resolve(
            device, conf.get("humidifier_current_humidity_dp")
        ),
    )


@dataclass
class WaterHeaterDefinition:
    """Resolved wrappers for a water heater entity."""

    switch_wrapper: DPCodeWrapper | None
    target_temp_wrapper: DPCodeWrapper | None
    current_temp_wrapper: DPCodeWrapper | None
    target_low_wrapper: DPCodeWrapper | None
    target_high_wrapper: DPCodeWrapper | None
    mode_wrapper: DPCodeWrapper | None


def get_water_heater_definition(
    device: Any, description: Any
) -> WaterHeaterDefinition | None:
    """Resolve the water heater wrappers; None if the switch DP is absent."""
    conf = getattr(description, "localtuya_conf", {}) or {}
    if (switch := resolve(device, conf.get("id"))) is None:
        return None
    return WaterHeaterDefinition(
        switch_wrapper=switch,
        target_temp_wrapper=resolve(device, conf.get("target_temperature_dp")),
        current_temp_wrapper=resolve(device, conf.get("current_temperature_dp")),
        target_low_wrapper=resolve(device, conf.get("target_temperature_low_dp")),
        target_high_wrapper=resolve(device, conf.get("target_temperature_high_dp")),
        mode_wrapper=resolve(device, conf.get("mode_dp")),
    )


@dataclass
class SelectDefinition:
    """Resolved wrapper for a select entity."""

    dpcode_wrapper: DPCodeWrapper | None


def get_select_definition(device: Any, description: Any) -> SelectDefinition | None:
    """Resolve the select wrapper; None if the DP is absent."""
    conf = getattr(description, "localtuya_conf", {}) or {}
    if (wrapper := resolve(device, conf.get("id"))) is None:
        return None
    return SelectDefinition(dpcode_wrapper=wrapper)


@dataclass
class NumberDefinition:
    """Resolved wrapper for a number entity."""

    dpcode_wrapper: DPCodeWrapper | None


def get_number_definition(device: Any, description: Any) -> NumberDefinition | None:
    """Resolve the number wrapper; None if the DP is absent."""
    conf = getattr(description, "localtuya_conf", {}) or {}
    if (wrapper := resolve(device, conf.get("id"))) is None:
        return None
    return NumberDefinition(dpcode_wrapper=wrapper)


@dataclass
class VacuumDefinition:
    """Resolved wrappers for a vacuum entity."""

    fan_speed_wrapper: DPCodeWrapper | None


def get_vacuum_definition(device: Any, description: Any) -> VacuumDefinition:
    """Resolve the vacuum fan-speed wrapper (the activity DP stays raw)."""
    conf = getattr(description, "localtuya_conf", {}) or {}
    return VacuumDefinition(
        fan_speed_wrapper=resolve(device, conf.get("fan_speed_dp")),
    )


@dataclass
class AlarmControlPanelDefinition:
    """Resolved wrapper for an alarm control panel entity."""

    dpcode_wrapper: DPCodeWrapper | None


def get_alarm_control_panel_definition(
    device: Any, description: Any
) -> AlarmControlPanelDefinition | None:
    """Resolve the alarm control panel wrapper; None if the DP is absent."""
    conf = getattr(description, "localtuya_conf", {}) or {}
    if (wrapper := resolve(device, conf.get("id"))) is None:
        return None
    return AlarmControlPanelDefinition(dpcode_wrapper=wrapper)


@dataclass
class DPCodeDefinition:
    """Resolved wrapper for a raw-passthrough (single primary DP) entity."""

    dpcode_wrapper: DPCodeWrapper | None


def _primary_dp_definition(device: Any, description: Any) -> DPCodeDefinition | None:
    """Resolve a single primary DP by dpcode; None if the DP is absent."""
    conf = getattr(description, "localtuya_conf", {}) or {}
    if (wrapper := resolve(device, conf.get("id"))) is None:
        return None
    return DPCodeDefinition(dpcode_wrapper=wrapper)


def get_sensor_definition(device: Any, description: Any) -> DPCodeDefinition | None:
    """Resolve a sensor's primary DP wrapper."""
    return _primary_dp_definition(device, description)


def get_binary_sensor_definition(
    device: Any, description: Any
) -> DPCodeDefinition | None:
    """Resolve a binary sensor's primary DP wrapper."""
    return _primary_dp_definition(device, description)


def get_siren_definition(device: Any, description: Any) -> DPCodeDefinition | None:
    """Resolve a siren's primary DP wrapper."""
    return _primary_dp_definition(device, description)


def get_valve_definition(device: Any, description: Any) -> DPCodeDefinition | None:
    """Resolve a valve's primary DP wrapper."""
    return _primary_dp_definition(device, description)


def get_lock_definition(device: Any, description: Any) -> DPCodeDefinition | None:
    """Resolve a lock's primary DP wrapper."""
    return _primary_dp_definition(device, description)


def get_remote_definition(device: Any, description: Any) -> DPCodeDefinition | None:
    """Resolve a remote's primary (send/control) DP wrapper."""
    return _primary_dp_definition(device, description)


def get_button_definition(device: Any, description: Any) -> DPCodeDefinition | None:
    """Resolve a button's primary DP wrapper."""
    return _primary_dp_definition(device, description)
