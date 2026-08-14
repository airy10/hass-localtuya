"""Tests for core/definitions.py (resolved wrapper definitions) + coordinator category/product_id."""

from types import SimpleNamespace

from custom_components.localtuya.const import (
    CONF_BRIGHTNESS_LOWER,
    CONF_BRIGHTNESS_UPPER,
    CONF_COLOR_TEMP_MAX_KELVIN,
    CONF_COLOR_TEMP_MIN_KELVIN,
    CONF_COLOR_TEMP_REVERSE,
    CONF_STATE_ON,
    TRANSPORT_BLE,
    TRANSPORT_ETHERNET,
)
from custom_components.localtuya.coordinator import TuyaDevice
from custom_components.localtuya.core.definitions import (
    get_alarm_control_panel_definition,
    get_binary_sensor_definition,
    get_button_definition,
    get_climate_definition,
    get_cover_definition,
    get_event_definition,
    get_fan_definition,
    get_humidifier_definition,
    get_light_definition,
    get_lock_definition,
    get_number_definition,
    get_remote_definition,
    get_select_definition,
    get_sensor_definition,
    get_siren_definition,
    get_switch_definition,
    get_vacuum_definition,
    get_valve_definition,
    get_water_heater_definition,
    resolve,
)
from custom_components.localtuya.core.dp_wrapper_decorators import (
    Base64Utf8RawEventWrapper,
    Base64Utf8StringEventWrapper,
    BinarySensorWrapper,
    BrightnessWrapper,
    ColorTempWrapper,
    SimpleEventEnumWrapper,
    StringColorWrapper,
)
from custom_components.localtuya.core.dp_wrappers import (
    DPCodeBooleanWrapper,
    DPCodeEnumWrapper,
    DPCodeIntegerWrapper,
)
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


def test_entity_config_from_description_gates_on_contains_any():
    from custom_components.localtuya.entity import entity_config_from_description

    def desc(contains_any):
        return LocalTuyaEntity(
            id=DPCode.RELAY_STATUS,
            condition_contains_any=contains_any,
        )

    specs = {
        "relay_status": {
            "dp_id": 38,
            "type": "Enum",
            "values": {"range": ["on", "off", "memory"]},
            "value": "on",
        },
    }

    # "on" is in the contains_any list -> description applies.
    config, primary_id = entity_config_from_description(
        _device(specs), desc(["on", "off", "memory"]), "select"
    )
    assert primary_id == "38"

    # "power_on" etc. are not in the reported value "on" -> gated out.
    config, primary_id = entity_config_from_description(
        _device(specs), desc(["power_on", "power_off", "last"]), "select"
    )
    assert primary_id is None


def test_entity_config_gates_on_persisted_detected_value():
    """Pre-connection gating uses the config-time detected value (dps_strings).

    Entities are created before the device connects, so ``status`` is empty.
    The detected value persisted at config time (e.g. ``relay_status`` reports
    ``on`` while the cloud enum range wrongly declares ``power_on``) must drive
    the ``contains_any`` variant selection.
    """
    from custom_components.localtuya.entity import entity_config_from_description

    def desc(contains_any):
        return LocalTuyaEntity(
            id=DPCode.RELAY_STATUS, condition_contains_any=contains_any
        )

    device = SimpleNamespace(
        function={},
        status_range={
            "relay_status": {
                "dp_id": "38",
                "type": "Enum",
                "values": {"range": ["power_off", "power_on", "last"]},
            },
        },
        status={},
        id="dev1",
        product_id="prod-1",
        persisted_dps_values={"38": "on"},
    )

    # "on" matches the persisted value -> the on/off/memory variant applies.
    config, primary_id = entity_config_from_description(
        device, desc(["on", "off", "memory"]), "select"
    )
    assert primary_id == "38"

    # "power_on" is not in the persisted value "on" -> gated out.
    config, primary_id = entity_config_from_description(
        device, desc(["power_on", "power_off", "last"]), "select"
    )
    assert primary_id is None


def test_described_entity_specs_dedups_primary_dp(monkeypatch):
    from custom_components.localtuya import entity as entity_mod
    from custom_components.localtuya.entity import _described_entity_specs

    specs = {
        "relay_status": {
            "dp_id": 38,
            "type": "Enum",
            "values": {"range": ["on", "off", "memory"]},
            "value": "on",
        },
    }
    device = _device(specs)

    desc_matching = LocalTuyaEntity(
        id=DPCode.RELAY_STATUS, condition_contains_any=["on", "off", "memory"]
    )
    desc_fallback = LocalTuyaEntity(id=DPCode.RELAY_STATUS)
    monkeypatch.setattr(
        entity_mod,
        "descriptions_for_platform",
        lambda d, dom: [desc_matching, desc_fallback],
    )

    resolved = _described_entity_specs(device, "select")
    # The matching variant wins; the unconditional fallback is dedup'd.
    assert len(resolved) == 1
    assert resolved[0][1] is desc_matching


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


# ---------------------------------------------------------------------------
# Phase 3-5 platform definitions
# ---------------------------------------------------------------------------

FAN_SPECS = {
    "switch_fan": {"dp_id": 1, "type": "Boolean", "values": None},
    "fan_speed": {
        "dp_id": 2,
        "type": "Integer",
        "values": {"min": 1, "max": 100, "scale": 0, "step": 1},
    },
    "fan_direction": {
        "dp_id": 3,
        "type": "Enum",
        "values": {"range": ["forward", "reverse"]},
    },
    "switch_horizontal": {"dp_id": 4, "type": "Boolean", "values": None},
    "fan_mode": {
        "dp_id": 5,
        "type": "Enum",
        "values": {"range": ["normal", "nature", "sleep"]},
    },
}


def test_fan_definition_resolves_wrappers_by_dpcode():
    desc = LocalTuyaEntity(
        id=DPCode.SWITCH_FAN,
        name="Fan",
        fan_speed_control=(DPCode.FAN_SPEED_PERCENT, DPCode.FAN_SPEED),
        fan_direction=DPCode.FAN_DIRECTION,
        fan_oscillating_control=(DPCode.SWITCH_HORIZONTAL, DPCode.SWITCH_VERTICAL),
        fan_mode=(DPCode.FAN_MODE, DPCode.MODE),
    )
    definition = get_fan_definition(_device(FAN_SPECS), desc)

    assert definition is not None
    assert isinstance(definition.switch_wrapper, DPCodeBooleanWrapper)
    assert definition.switch_wrapper.dpcode == DPCode.SWITCH_FAN
    assert isinstance(definition.speed_wrapper, DPCodeIntegerWrapper)
    assert definition.speed_wrapper.dpcode == DPCode.FAN_SPEED
    assert isinstance(definition.direction_wrapper, DPCodeEnumWrapper)
    assert definition.oscillate_wrapper.dpcode == DPCode.SWITCH_HORIZONTAL
    assert isinstance(definition.mode_wrapper, DPCodeEnumWrapper)
    assert definition.mode_wrapper.dpcode == DPCode.FAN_MODE
    assert definition.mode_wrapper.options == ["normal", "nature", "sleep"]


def test_fan_definition_gates_on_absent_switch():
    desc = LocalTuyaEntity(id=DPCode.SWITCH_FAN, name="Fan")
    assert get_fan_definition(_device({}), desc) is None


def test_climate_definition_resolves_wrappers_by_dpcode():
    specs = {
        "switch": {"dp_id": 1, "type": "Boolean", "values": None},
        "temp_set": {
            "dp_id": 2,
            "type": "Integer",
            "values": {"min": 0, "max": 1000, "scale": 1, "step": 1},
        },
        "temp_current": {
            "dp_id": 3,
            "type": "Integer",
            "values": {"min": 0, "max": 1000, "scale": 1, "step": 1},
        },
        "systemmode": {
            "dp_id": 4,
            "type": "Enum",
            "values": {"range": ["auto", "cold", "hot"]},
        },
    }
    desc = LocalTuyaEntity(
        id=DPCode.SWITCH,
        target_temperature_dp=DPCode.TEMP_SET,
        current_temperature_dp=DPCode.TEMP_CURRENT,
        hvac_mode_dp=DPCode.SYSTEMMODE,
    )
    definition = get_climate_definition(_device(specs), desc)

    assert definition is not None
    assert isinstance(definition.switch_wrapper, DPCodeBooleanWrapper)
    assert definition.target_temp_wrapper.dpcode == DPCode.TEMP_SET
    assert definition.current_temp_wrapper.dpcode == DPCode.TEMP_CURRENT
    assert definition.hvac_mode_wrapper.dpcode == DPCode.SYSTEMMODE
    assert definition.hvac_action_wrapper is None
    assert definition.preset_wrapper is None


def test_cover_definition_resolves_set_position():
    desc = LocalTuyaEntity(
        id=DPCode.CONTROL,
        name="Curtain",
        set_position_dp=DPCode.PERCENT_CONTROL,
    )
    definition = get_cover_definition(
        _device(
            {
                "percent_control": {
                    "dp_id": 7,
                    "type": "Integer",
                    "values": {"min": 0, "max": 100, "scale": 0, "step": 1},
                }
            }
        ),
        desc,
    )
    assert definition.set_position_wrapper is not None
    assert definition.set_position_wrapper.dpcode == DPCode.PERCENT_CONTROL


def test_humidifier_definition_resolves_wrappers():
    specs = {
        "switch": {"dp_id": 1, "type": "Boolean", "values": None},
        "mode": {"dp_id": 2, "type": "Enum", "values": {"range": ["large", "small"]}},
        "humidity_set": {
            "dp_id": 3,
            "type": "Integer",
            "values": {"min": 0, "max": 100, "scale": 0, "step": 1},
        },
    }
    desc = LocalTuyaEntity(
        id=DPCode.SWITCH,
        humidifier_mode_dp=DPCode.MODE,
        humidifier_set_humidity_dp=DPCode.HUMIDITY_SET,
    )
    definition = get_humidifier_definition(_device(specs), desc)
    assert definition is not None
    assert definition.switch_wrapper.dpcode == DPCode.SWITCH
    assert definition.mode_wrapper.dpcode == DPCode.MODE
    assert definition.target_humidity_wrapper.dpcode == DPCode.HUMIDITY_SET


def test_water_heater_definition_resolves_wrappers():
    specs = {
        "switch": {"dp_id": 1, "type": "Boolean", "values": None},
        "temp_set": {
            "dp_id": 2,
            "type": "Integer",
            "values": {"min": 0, "max": 1000, "scale": 1, "step": 1},
        },
        "mode": {"dp_id": 3, "type": "Enum", "values": {"range": ["smart"]}},
    }
    desc = LocalTuyaEntity(
        id=DPCode.SWITCH,
        target_temperature_dp=DPCode.TEMP_SET,
        mode_dp=DPCode.MODE,
    )
    definition = get_water_heater_definition(_device(specs), desc)
    assert definition is not None
    assert definition.switch_wrapper.dpcode == DPCode.SWITCH
    assert definition.target_temp_wrapper.dpcode == DPCode.TEMP_SET
    assert definition.mode_wrapper.dpcode == DPCode.MODE


def test_binary_sensor_definition_wraps_with_on_value():
    """The binary sensor on/off conversion lives in the wrapper (core parity)."""
    specs = {
        "gas_sensor_state": {
            "dp_id": 9,
            "type": "Enum",
            "values": {"range": ["alarm", "normal"]},
        },
    }
    desc = LocalTuyaEntity(
        id=DPCode.GAS_SENSOR_STATE, custom_configs={CONF_STATE_ON: "alarm"}
    )
    definition = get_binary_sensor_definition(_device(specs), desc)
    assert definition is not None
    assert isinstance(definition.dpcode_wrapper, BinarySensorWrapper)
    assert definition.dpcode_wrapper.read_device_status(
        SimpleNamespace(status={"gas_sensor_state": "alarm"})
    ) is True
    assert definition.dpcode_wrapper.read_device_status(
        SimpleNamespace(status={"gas_sensor_state": "normal"})
    ) is False


def test_event_definition_resolves_wrapper_by_type():
    """Event wrappers are chosen per-description (core's wrapper_class field)."""
    specs = {
        "switch_mode1": {
            "dp_id": 1,
            "type": "Enum",
            "values": {"range": ["single_click", "double_click"]},
        },
        "alarm_message": {"dp_id": 2, "type": "String", "values": None},
        "doorbell_pic": {"dp_id": 3, "type": "Raw", "values": None},
    }

    enum_desc = LocalTuyaEntity(id=DPCode.SWITCH_MODE1)
    enum_def = get_event_definition(_device(specs), enum_desc)
    assert enum_def is not None
    assert isinstance(enum_def.event_wrapper, SimpleEventEnumWrapper)
    assert enum_def.event_wrapper.options == ["single_click", "double_click"]

    string_desc = LocalTuyaEntity(
        id=DPCode.ALARM_MESSAGE, wrapper_class=Base64Utf8StringEventWrapper
    )
    string_def = get_event_definition(_device(specs), string_desc)
    assert string_def is not None
    assert isinstance(string_def.event_wrapper, Base64Utf8StringEventWrapper)
    assert string_def.event_wrapper.options == ["triggered"]

    raw_desc = LocalTuyaEntity(
        id=DPCode.DOORBELL_PIC, wrapper_class=Base64Utf8RawEventWrapper
    )
    raw_def = get_event_definition(_device(specs), raw_desc)
    assert raw_def is not None
    assert isinstance(raw_def.event_wrapper, Base64Utf8RawEventWrapper)


def test_event_definition_gates_on_absent_dp():
    desc = LocalTuyaEntity(id=DPCode.ALARM_MESSAGE)
    assert get_event_definition(_device({}), desc) is None


def test_select_number_and_raw_definitions_resolve_primary():
    specs = {"switch": {"dp_id": 1, "type": "Boolean", "values": None}}
    select_desc = LocalTuyaEntity(id=DPCode.SWITCH, name="Mode")

    select = get_select_definition(_device(specs), select_desc)
    assert select is not None and select.dpcode_wrapper.dpcode == DPCode.SWITCH

    number = get_number_definition(_device(specs), select_desc)
    assert number is not None and number.dpcode_wrapper.dpcode == DPCode.SWITCH

    alarm = get_alarm_control_panel_definition(_device(specs), select_desc)
    assert alarm is not None and alarm.dpcode_wrapper.dpcode == DPCode.SWITCH

    sensor = get_sensor_definition(_device(specs), select_desc)
    assert sensor is not None and sensor.dpcode_wrapper.dpcode == DPCode.SWITCH

    binary = get_binary_sensor_definition(_device(specs), select_desc)
    assert binary is not None and binary.dpcode_wrapper.dpcode == DPCode.SWITCH

    siren = get_siren_definition(_device(specs), select_desc)
    assert siren is not None and siren.dpcode_wrapper.dpcode == DPCode.SWITCH

    valve = get_valve_definition(_device(specs), select_desc)
    assert valve is not None and valve.dpcode_wrapper.dpcode == DPCode.SWITCH

    lock = get_lock_definition(_device(specs), select_desc)
    assert lock is not None and lock.dpcode_wrapper.dpcode == DPCode.SWITCH

    remote = get_remote_definition(_device(specs), select_desc)
    assert remote is not None and remote.dpcode_wrapper.dpcode == DPCode.SWITCH

    button = get_button_definition(_device(specs), select_desc)
    assert button is not None and button.dpcode_wrapper.dpcode == DPCode.SWITCH


def test_vacuum_definition_resolves_fan_speed():
    specs = {
        "fan_speed_enum": {
            "dp_id": 9,
            "type": "Enum",
            "values": {"range": ["low", "normal", "high"]},
        }
    }
    desc = LocalTuyaEntity(id=DPCode.POWER_GO, fan_speed_dp=DPCode.FAN_SPEED_ENUM)
    definition = get_vacuum_definition(_device(specs), desc)
    assert definition.fan_speed_wrapper is not None
    assert definition.fan_speed_wrapper.dpcode == DPCode.FAN_SPEED_ENUM
