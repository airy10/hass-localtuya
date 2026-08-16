"""Per-product entity mapping tables for BLE auto-entity generation.

This module mirrors the ``ha_tuya_ble`` per-product mapping tables
(``get_mapping_by_device``) and produces entity config dicts in the localtuya
config-driven format, so BLE devices with a known product can auto-create
entities from their ``category``/``product_id`` without manual numeric-DP
configuration. Category-table derivation (the shared, definition-driven path)
lives in ``entity.py::_described_entity_specs`` and applies to both transports.

Each mapping entry carries the platform, the datapoint id, the entity config
dict (in the same shape as ``CONF_ENTITIES`` entries), and optional gating
metadata (``force_add``, ``dp_type``, ``is_available``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.const import (
    CONF_DEVICE_CLASS,
    CONF_FRIENDLY_NAME,
    CONF_ID,
    CONF_PLATFORM,
    CONF_UNIT_OF_MEASUREMENT,
    Platform,
    UnitOfRatio,
)

from ..const import (
    CONF_BITMAP_MASK,
    CONF_CURRENT_TEMPERATURE_DP,
    CONF_ENTITY_ENABLED_DEFAULT,
    CONF_HVAC_ACTION_DP,
    CONF_HVAC_ACTION_SET,
    CONF_HVAC_MODE_DP,
    CONF_HVAC_MODE_SET,
    CONF_HVAC_SWITCH_DP,
    CONF_ICONS,
    CONF_IS_AVAILABLE,
    CONF_MAX_TEMP,
    CONF_MIN_TEMP,
    CONF_PATTERN,
    CONF_PRECISION,
    CONF_RESTORE_ON_RECONNECT,
    CONF_SCALING,
    CONF_STATE_CLASS,
    CONF_TARGET_TEMPERATURE_DP,
    CONF_TEMPERATURE_STEP,
)
from .tuya_ble_lib.const import TuyaBLEDataPointType

# ---------------------------------------------------------------------------
# Mapping dataclasses
# ---------------------------------------------------------------------------


@dataclass
class TuyaEntityMapping:
    """A single auto-generated entity mapping.

    ``config`` is an entity config dict in the same shape as a
    ``CONF_ENTITIES`` entry (``CONF_ID``, ``CONF_PLATFORM``, ...). When
    ``force_add`` is False the entity is only created if the device exposes a
    datapoint with ``dp_id`` and (optionally) ``dp_type``.
    """

    dp_id: int
    platform: Platform
    config: dict[str, Any]
    force_add: bool = True
    dp_type: TuyaBLEDataPointType | None = None
    is_available: Callable[..., bool] | None = None

    def __post_init__(self) -> None:
        """Fill in the config dict defaults from the mapping fields."""
        self.config.setdefault(CONF_ID, str(self.dp_id))
        self.config.setdefault(CONF_PLATFORM, self.platform.value)
        if self.is_available is not None:
            self.config.setdefault(CONF_IS_AVAILABLE, self.is_available)


@dataclass
class TuyaCategoryMapping:
    """Per-category mapping table with optional per-product overrides."""

    products: dict[str, list[TuyaEntityMapping]] | None = None
    mapping: list[TuyaEntityMapping] | None = None


# ---------------------------------------------------------------------------
# Helper builders
# ---------------------------------------------------------------------------


def _sensor(
    dp_id: int,
    name: str,
    *,
    device_class: str | None = None,
    unit: str | None = None,
    state_class: str | None = None,
    scaling: float | None = None,
    icons: list[str] | None = None,
    enabled_default: bool = True,
    force_add: bool = True,
    dp_type: TuyaBLEDataPointType | None = None,
    is_available: Callable[..., bool] | None = None,
) -> TuyaEntityMapping:
    """Build a sensor mapping."""
    config: dict[str, Any] = {CONF_FRIENDLY_NAME: name}
    if device_class is not None:
        config[CONF_DEVICE_CLASS] = device_class
    if unit is not None:
        config[CONF_UNIT_OF_MEASUREMENT] = unit
    if state_class is not None:
        config[CONF_STATE_CLASS] = state_class
    if scaling is not None:
        config[CONF_SCALING] = scaling
    if icons is not None:
        config[CONF_ICONS] = icons
    config[CONF_ENTITY_ENABLED_DEFAULT] = enabled_default
    return TuyaEntityMapping(
        dp_id=dp_id,
        platform=Platform.SENSOR,
        config=config,
        force_add=force_add,
        dp_type=dp_type,
        is_available=is_available,
    )


def _switch(
    dp_id: int,
    name: str,
    *,
    bitmap_mask: str | None = None,
    enabled_default: bool = True,
    force_add: bool = True,
    dp_type: TuyaBLEDataPointType | None = None,
    is_available: Callable[..., bool] | None = None,
) -> TuyaEntityMapping:
    """Build a switch mapping."""
    config: dict[str, Any] = {
        CONF_FRIENDLY_NAME: name,
        CONF_RESTORE_ON_RECONNECT: False,
        CONF_ENTITY_ENABLED_DEFAULT: enabled_default,
    }
    if bitmap_mask is not None:
        config[CONF_BITMAP_MASK] = bitmap_mask
    return TuyaEntityMapping(
        dp_id=dp_id,
        platform=Platform.SWITCH,
        config=config,
        force_add=force_add,
        dp_type=dp_type,
        is_available=is_available,
    )


def _text(
    dp_id: int,
    name: str,
    *,
    pattern: str | None = None,
    enabled_default: bool = True,
    force_add: bool = True,
    dp_type: TuyaBLEDataPointType | None = None,
    is_available: Callable[..., bool] | None = None,
) -> TuyaEntityMapping:
    """Build a text mapping."""
    config: dict[str, Any] = {
        CONF_FRIENDLY_NAME: name,
        CONF_ENTITY_ENABLED_DEFAULT: enabled_default,
    }
    if pattern is not None:
        config[CONF_PATTERN] = pattern
    return TuyaEntityMapping(
        dp_id=dp_id,
        platform=Platform.TEXT,
        config=config,
        force_add=force_add,
        dp_type=dp_type,
        is_available=is_available,
    )


def _climate(
    dp_id: int,
    name: str,
    *,
    target_temperature_dp: int,
    current_temperature_dp: int | None = None,
    hvac_switch_dp: int | None = None,
    hvac_mode_dp: int | None = None,
    hvac_mode_set: dict[str, str] | None = None,
    hvac_action_dp: int | None = None,
    hvac_action_set: dict[str, str] | None = None,
    min_temp: float = 5.0,
    max_temp: float = 30.0,
    temperature_step: str = "0.5",
    precision: str = "0.1",
    force_add: bool = True,
) -> TuyaEntityMapping:
    """Build a climate mapping."""
    config: dict[str, Any] = {
        CONF_FRIENDLY_NAME: name,
        CONF_TARGET_TEMPERATURE_DP: str(target_temperature_dp),
        CONF_MIN_TEMP: min_temp,
        CONF_MAX_TEMP: max_temp,
        CONF_TEMPERATURE_STEP: temperature_step,
        CONF_PRECISION: precision,
    }
    if current_temperature_dp is not None:
        config[CONF_CURRENT_TEMPERATURE_DP] = str(current_temperature_dp)
    if hvac_switch_dp is not None:
        config[CONF_HVAC_SWITCH_DP] = str(hvac_switch_dp)
    if hvac_mode_dp is not None:
        config[CONF_HVAC_MODE_DP] = str(hvac_mode_dp)
    if hvac_mode_set is not None:
        config[CONF_HVAC_MODE_SET] = hvac_mode_set
    if hvac_action_dp is not None:
        config[CONF_HVAC_ACTION_DP] = str(hvac_action_dp)
    if hvac_action_set is not None:
        config[CONF_HVAC_ACTION_SET] = hvac_action_set
    return TuyaEntityMapping(
        dp_id=dp_id,
        platform=Platform.CLIMATE,
        config=config,
        force_add=force_add,
    )


# ---------------------------------------------------------------------------
# Mapping registry
# ---------------------------------------------------------------------------

# Fingerbot program text pattern: position[/delay] steps separated by ';'
# (e.g. "50/1000;100/500"), position/delay in 0-100 / 0-99 range.
FINGERBOT_PROGRAM_PATTERN = (
    r"^((\d{1,2}|100)(/\d{1,2})?)(;((\d{1,2}|100)(/\d{1,2})?))+$"
)

MAPPINGS: dict[str, TuyaCategoryMapping] = {
    # CO2 Detector
    "co2bj": TuyaCategoryMapping(
        products={
            "59s19z5m": [
                _sensor(
                    1,
                    "Carbon dioxide alarm",
                    device_class="enum",
                    icons=["mdi:molecule-co2", "mdi:molecule-co2"],
                ),
                _sensor(
                    2,
                    "Carbon dioxide",
                    device_class="carbon_dioxide",
                    unit=UnitOfRatio.PARTS_PER_MILLION,
                    state_class="measurement",
                ),
                _sensor(
                    15,
                    "Battery",
                    device_class="battery",
                    unit="%",
                    state_class="measurement",
                ),
                _sensor(
                    18,
                    "Temperature",
                    device_class="temperature",
                    unit="°C",
                    state_class="measurement",
                    scaling=0.1,
                ),
                _switch(
                    11,
                    "Carbon dioxide severely exceed alarm",
                    bitmap_mask="01",
                    enabled_default=False,
                ),
                _switch(
                    11,
                    "Low battery alarm",
                    bitmap_mask="02",
                    enabled_default=False,
                ),
                _switch(13, "Carbon dioxide alarm switch", enabled_default=False),
            ],
        },
    ),
    # Thermostatic Radiator Valve
    "wk": TuyaCategoryMapping(
        products={
            "drlajpqc": [
                _climate(
                    103,
                    "Thermostatic radiator valve",
                    target_temperature_dp=103,
                    current_temperature_dp=102,
                    hvac_switch_dp=101,
                    min_temp=5.0,
                    max_temp=30.0,
                    temperature_step="0.5",
                ),
                _sensor(
                    102,
                    "Current temperature",
                    device_class="temperature",
                    unit="°C",
                    state_class="measurement",
                    scaling=0.1,
                ),
                _sensor(
                    105,
                    "Battery power alarm",
                    device_class="battery",
                    unit="%",
                    state_class="measurement",
                ),
            ],
            "nhj2j7su": [
                _climate(
                    103,
                    "Thermostatic radiator valve",
                    target_temperature_dp=103,
                    current_temperature_dp=102,
                    hvac_switch_dp=101,
                    min_temp=5.0,
                    max_temp=30.0,
                    temperature_step="0.5",
                ),
                _sensor(
                    102,
                    "Current temperature",
                    device_class="temperature",
                    unit="°C",
                    state_class="measurement",
                    scaling=0.1,
                ),
                _sensor(
                    105,
                    "Battery power alarm",
                    device_class="battery",
                    unit="%",
                    state_class="measurement",
                ),
            ],
        },
    ),
    # Fingerbot (CubeTouch 1s and II, Fingerbot Plus, Fingerbot)
    "szjqr": TuyaCategoryMapping(
        products={
            "3yqdo5yt": [
                _switch(1, "Fingerbot"),
                _switch(4, "Reverse positions", enabled_default=False),
            ],
            "xhf790if": [
                _switch(1, "Fingerbot"),
                _switch(4, "Reverse positions", enabled_default=False),
            ],
            **dict.fromkeys(
                [
                    "blliqpsj",
                    "ndvkgsrm",
                    "yiihr7zh",
                    "neq16kgd",
                ],  # Fingerbot Plus
                [
                    _text(
                        121,
                        "Fingerbot Program",
                        pattern=FINGERBOT_PROGRAM_PATTERN,
                    ),
                ],
            ),
            **dict.fromkeys(
                [
                    "ltak7e1p",
                    "y6kttvd6",
                    "yrnk7mnn",
                    "nvr2rocq",
                    "bnt7wajf",
                    "rvdceqjh",
                    "5xhbk964",
                ],  # Fingerbot
                [
                    _text(
                        121,
                        "Fingerbot Program",
                        pattern=FINGERBOT_PROGRAM_PATTERN,
                    ),
                ],
            ),
        },
    ),
}


def get_mapping_by_device(device) -> list[TuyaEntityMapping]:
    """Return the per-product entity mappings for a device.

    Mirrors ``ha_tuya_ble``'s ``get_mapping_by_device``: resolve the category
    table, then the per-product override, falling back to the category-level
    mapping when the product is unknown. Returns an empty list when no
    hardcoded mapping exists — the shared category-table derivation
    (``entity.py::_described_entity_specs``) then supplies entities from the
    ``ha_entities`` tables for both transports.
    """
    category = MAPPINGS.get(device.category)
    if category is None:
        return []
    if category.products is not None:
        if (product_mapping := category.products.get(device.product_id)) is not None:
            return product_mapping
    if category.mapping is not None:
        return category.mapping
    return []
