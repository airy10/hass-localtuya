"""Tests for core/definitions.py (resolved wrapper definitions) + coordinator category/product_id."""

from types import SimpleNamespace

from custom_components.localtuya.const import (
    CONF_BRIGHTNESS_LOWER,
    CONF_BRIGHTNESS_UPPER,
    CONF_COLOR_TEMP_MAX_KELVIN,
    CONF_COLOR_TEMP_MIN_KELVIN,
    CONF_COLOR_TEMP_REVERSE,
    TRANSPORT_BLE,
    TRANSPORT_ETHERNET,
)
from custom_components.localtuya.coordinator import TuyaDevice
from custom_components.localtuya.core.definitions import (
    get_light_definition,
    get_switch_definition,
    resolve,
)
from custom_components.localtuya.core.dp_wrapper_decorators import (
    BrightnessWrapper,
    ColorTempWrapper,
    StringColorWrapper,
)
from custom_components.localtuya.core.dp_wrappers import DPCodeBooleanWrapper, DPCodeEnumWrapper
from custom_components.localtuya.core.ha_entities.base import DPCode, LocalTuyaEntity


def _device(specs):
    """Build a duck-typed device exposing the core-compatible spec surface."""
    return SimpleNamespace(
        function={},
        status_range=specs,
        status={},
        id="dev1",
        product_id="prod-1",
    )


LIGHT_SPECS = {
    "switch_led": {"dp_id": 1, "type": "Boolean", "values": None},
    "bright_value": {
        "dp_id": 2,
        "type": "Integer",
        "values": {"min": 0, "max": 1000, "scale": 0, "step": 1},
    },
    "work_mode": {
        "dp_id": 3,
        "type": "Enum",
        "values": {"range": ["white", "colour", "scene"]},
    },
    "colour_data": {"dp_id": 4, "type": "String", "values": None},
    "temp_value": {
        "dp_id": 5,
        "type": "Integer",
        "values": {"min": 0, "max": 1000, "scale": 0, "step": 1},
    },
}


def _light_description():
    return LocalTuyaEntity(
        id=DPCode.SWITCH_LED,
        name=None,
        color_mode=DPCode.WORK_MODE,
        brightness=(DPCode.BRIGHT_VALUE_V2, DPCode.BRIGHT_VALUE),
        color_temp=(DPCode.TEMP_VALUE_V2, DPCode.TEMP_VALUE),
        color=(DPCode.COLOUR_DATA_V2, DPCode.COLOUR_DATA),
        custom_configs={
            CONF_BRIGHTNESS_LOWER: 29,
            CONF_BRIGHTNESS_UPPER: 1000,
            CONF_COLOR_TEMP_MIN_KELVIN: 2700,
            CONF_COLOR_TEMP_MAX_KELVIN: 6500,
            CONF_COLOR_TEMP_REVERSE: False,
        },
    )


# ---------------------------------------------------------------------------
# resolve()
# ---------------------------------------------------------------------------


def test_resolve_returns_none_for_missing_dpcode():
    assert resolve(_device({}), DPCode.SWITCH_LED) is None


def test_resolve_prefers_first_present_tuple_alternative():
    wrapper = resolve(_device(LIGHT_SPECS), (DPCode.BRIGHT_VALUE_V2, DPCode.BRIGHT_VALUE))
    assert wrapper is not None
    assert wrapper.dpcode == DPCode.BRIGHT_VALUE


def test_resolve_applies_decorator():
    wrapper = resolve(
        _device(LIGHT_SPECS),
        DPCode.BRIGHT_VALUE,
        BrightnessWrapper,
        lower=29,
        upper=1000,
    )
    assert isinstance(wrapper, BrightnessWrapper)


def test_resolve_handles_none_dpcode():
    assert resolve(_device(LIGHT_SPECS), None) is None


# ---------------------------------------------------------------------------
# get_switch_definition()
# ---------------------------------------------------------------------------


def test_switch_definition_gates_on_absent_primary_dp():
    desc = LocalTuyaEntity(id=DPCode.SWITCH_LED, name=None)
    assert get_switch_definition(_device({}), desc) is None


def test_switch_definition_resolves_wrapper():
    desc = LocalTuyaEntity(id=DPCode.SWITCH_LED, name=None)
    definition = get_switch_definition(_device(LIGHT_SPECS), desc)
    assert definition is not None
    assert isinstance(definition.switch_wrapper, DPCodeBooleanWrapper)


# ---------------------------------------------------------------------------
# get_light_definition()
# ---------------------------------------------------------------------------


def test_light_definition_resolves_and_decorates_wrappers():
    definition = get_light_definition(_device(LIGHT_SPECS), _light_description())

    assert definition is not None
    assert definition.switch_wrapper is not None
    assert isinstance(definition.brightness_wrapper, BrightnessWrapper)
    assert isinstance(definition.color_temp_wrapper, ColorTempWrapper)
    assert isinstance(definition.color_data_wrapper, StringColorWrapper)
    assert isinstance(definition.color_mode_wrapper, DPCodeEnumWrapper)
    assert definition.color_mode_wrapper.options == ["white", "colour", "scene"]


def test_light_definition_gates_on_absent_switch_dp():
    device = _device({k: v for k, v in LIGHT_SPECS.items() if k != "switch_led"})
    assert get_light_definition(device, _light_description()) is None


def test_light_definition_resolves_cloud_value_defaults():
    from custom_components.localtuya.core.ha_entities.base import CLOUD_VALUE

    desc = _light_description()
    desc.entity_configs[CONF_BRIGHTNESS_UPPER] = CLOUD_VALUE(
        800, "brightness", "max"
    )
    definition = get_light_definition(_device(LIGHT_SPECS), desc)
    assert definition is not None
    assert definition.brightness_wrapper._upper == 800


# ---------------------------------------------------------------------------
# TuyaDevice.category / product_id
# ---------------------------------------------------------------------------


def test_category_and_product_id_ble_passthrough():
    tuya_device = object.__new__(TuyaDevice)
    tuya_device._device_config = SimpleNamespace(transport=TRANSPORT_BLE)
    ble = SimpleNamespace(category="dd", product_id="prod-ble")
    tuya_device._interface = SimpleNamespace(ble_device=ble)

    assert tuya_device.category == "dd"
    assert tuya_device.product_id == "prod-ble"


def test_category_and_product_id_ethernet_from_cloud_data(monkeypatch):
    tuya_device = object.__new__(TuyaDevice)
    tuya_device._device_config = SimpleNamespace(transport=TRANSPORT_ETHERNET)
    tuya_device._interface = None
    monkeypatch.setattr(
        tuya_device,
        "_cloud_device_data",
        lambda: {"category": "dj", "product_id": "prod-eth"},
    )

    assert tuya_device.category == "dj"
    assert tuya_device.product_id == "prod-eth"


def test_category_falls_back_to_cloud_data_when_ble_has_none(monkeypatch):
    tuya_device = object.__new__(TuyaDevice)
    tuya_device._device_config = SimpleNamespace(transport=TRANSPORT_BLE)
    tuya_device._interface = SimpleNamespace(
        ble_device=SimpleNamespace(category=None, product_id=None)
    )
    monkeypatch.setattr(
        tuya_device,
        "_cloud_device_data",
        lambda: {"category": "dd", "product_id": "prod-1"},
    )

    assert tuya_device.category == "dd"
    assert tuya_device.product_id == "prod-1"


# ---------------------------------------------------------------------------
# entity_config_from_description (description -> _config adapter)
# ---------------------------------------------------------------------------


def test_entity_config_from_description_builds_config():
    from homeassistant.const import CONF_ID, CONF_PLATFORM
    from custom_components.localtuya.entity import entity_config_from_description

    desc = _light_description()
    config, primary_id = entity_config_from_description(
        _device(LIGHT_SPECS), desc, "light"
    )

    assert primary_id == "1"
    assert config[CONF_ID] == "1"
    assert config[CONF_PLATFORM] == "light"
    assert config["brightness"] == "2"
    assert config["color_mode"] == "3"
    assert config["color"] == "4"
    assert config["color_temp"] == "5"
    assert config[CONF_BRIGHTNESS_LOWER] == 29
    assert config[CONF_BRIGHTNESS_UPPER] == 1000
    assert config[CONF_COLOR_TEMP_MIN_KELVIN] == 2700
    assert config[CONF_COLOR_TEMP_MAX_KELVIN] == 6500


def test_entity_config_from_description_gates_on_absent_primary():
    from custom_components.localtuya.entity import entity_config_from_description

    device = _device({k: v for k, v in LIGHT_SPECS.items() if k != "switch_led"})
    config, primary_id = entity_config_from_description(
        device, _light_description(), "light"
    )

    assert primary_id is None
    assert "id" not in config


def test_entity_config_from_description_resolves_cloud_values():
    from custom_components.localtuya.core.ha_entities.base import CLOUD_VALUE
    from custom_components.localtuya.entity import entity_config_from_description

    desc = _light_description()
    desc.entity_configs[CONF_BRIGHTNESS_UPPER] = CLOUD_VALUE(
        800, "brightness", "max"
    )
    config, _ = entity_config_from_description(_device(LIGHT_SPECS), desc, "light")

    assert config[CONF_BRIGHTNESS_UPPER] == 800


# ---------------------------------------------------------------------------
# descriptions_for_platform (category -> ha_entities table lookup)
# ---------------------------------------------------------------------------


def test_descriptions_for_platform_uses_category():
    from custom_components.localtuya.entity import descriptions_for_platform

    descs = descriptions_for_platform(SimpleNamespace(category="kg"), "switch")
    assert len(descs) > 0
    assert all(getattr(d, "localtuya_conf", {}).get("id") is not None for d in descs)


def test_descriptions_for_platform_empty_without_category():
    from custom_components.localtuya.entity import descriptions_for_platform

    assert descriptions_for_platform(SimpleNamespace(category=None), "switch") == []
    assert descriptions_for_platform(SimpleNamespace(category="unknown"), "switch") == []
