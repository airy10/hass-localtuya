"""Resolved per-platform wrapper definitions (core's ``get_default_definition``).

Core tuya resolves each entity's wrappers *by dpcode* from a
``DeviceCategory -> EntityDescription`` table, gated on the primary DP being
present in the device spec. This module is the localtuya equivalent: given a
device (exposing the core-compatible ``function``/``status_range``/``status``
surface) and a ``LocalTuyaEntity`` description, it resolves the wrappers by
dpcode and applies the relevant conversion decorators from
``core/dp_wrapper_decorators.py``.

This is the runtime half of SPEC_DEFINITION_DRIVEN_RUNTIME.md. Only light and
switch are implemented (Phases 1-2); the remaining platforms are added in
Phases 3-5.
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
    "LightDefinition",
    "SwitchDefinition",
    "get_light_definition",
    "get_switch_definition",
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
