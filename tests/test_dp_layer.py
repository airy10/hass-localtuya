"""Tests for the vendored core-alignment capability layer (Phase 1).

Covers core/dp_types.py + core/dp_wrappers.py + the TuyaDevice spec
surface (function/status_range/status/dp_type).
"""

from types import SimpleNamespace

import pytest

from custom_components.localtuya.const import DPType
from custom_components.localtuya.coordinator import TuyaDevice
from custom_components.localtuya.core.dp_types import (
    BooleanTypeInformation,
    EnumTypeInformation,
    IntegerTypeInformation,
    JsonTypeInformation,
    PrepareSetValueError,
    RawTypeInformation,
    StringTypeInformation,
)
from custom_components.localtuya.core.dp_wrappers import (
    DPCodeBooleanWrapper,
    DPCodeEnumWrapper,
    DPCodeIntegerWrapper,
    DPCodeRawWrapper,
    DPCodeStringWrapper,
    SetValueOutOfRangeError,
    dp_wrapper_by_code,
    dp_wrapper_by_id,
)


def _fake_device(function=None, status_range=None, status=None, id="dev"):
    """Build a duck-typed spec/status surface like core's CustomerDevice."""
    return SimpleNamespace(
        id=id,
        product_id="prod",
        function=function or {},
        status_range=status_range or {},
        status=status or {},
    )


def _enum_spec(values: dict) -> dict:
    return {"type": DPType.ENUM, "values": values}


def _int_spec(min=0, max=100, scale=0, step=1) -> dict:
    return {"type": DPType.INTEGER, "values": {"min": min, "max": max, "scale": scale, "step": step}}


def test_enum_type_information_from_dict_values():
    device = _fake_device(status_range={"work_mode": _enum_spec({"0": "color", "1": "white"})})
    ti = EnumTypeInformation.find_dpcode(device, "work_mode")
    assert ti is not None
    assert ti.range == ["color", "white"]
    assert ti.read_device_value(_fake_device(status={"work_mode": "color"})) == "color"


def test_enum_type_information_from_json_string_values():
    device = _fake_device(
        status_range={"work_mode": {"type": DPType.ENUM, "values": '{"range": ["a", "b"]}'}}
    )
    ti = EnumTypeInformation.find_dpcode(device, "work_mode")
    assert ti is not None
    assert ti.range == ["a", "b"]


def test_enum_prepare_set_value_validates_range():
    ti = EnumTypeInformation(dpcode="m", type_data="", report_type=None, range=["a", "b"])
    assert ti.prepare_set_value(None, "a") == "a"
    with pytest.raises(PrepareSetValueError):
        ti.prepare_set_value(None, "c")


def test_integer_type_information_scaling():
    device = _fake_device(status_range={"temp": _int_spec(min=0, max=300, scale=1, step=1)})
    ti = IntegerTypeInformation.find_dpcode(device, "temp")
    assert ti is not None
    assert ti.min == 0 and ti.max == 300 and ti.scale == 1
    assert ti.read_device_value(_fake_device(status={"temp": 255})) == 25.5
    assert ti.prepare_set_value(None, 25.5) == 255


def test_integer_prepare_set_value_out_of_range():
    ti = IntegerTypeInformation(
        dpcode="t", type_data="", report_type=None, min=0, max=10, scale=0, step=1
    )
    with pytest.raises(PrepareSetValueError):
        ti.prepare_set_value(None, 11)


def test_boolean_type_information_reads_and_validates():
    ti = BooleanTypeInformation(dpcode="sw", type_data="", report_type=None)
    assert ti.read_device_value(_fake_device(status={"sw": True})) is True
    assert ti.read_device_value(_fake_device(status={"sw": "garbage"})) is None
    assert ti.prepare_set_value(None, True) is True
    with pytest.raises(PrepareSetValueError):
        ti.prepare_set_value(None, 1)


def test_json_and_raw_and_string_type_information():
    json_ti = JsonTypeInformation(dpcode="j", type_data="", report_type=None)
    assert json_ti.read_device_value(_fake_device(status={"j": '{"a": 1}'})) == {"a": 1}
    assert json_ti.read_device_value(_fake_device(status={"j": "{bad"})) is None

    raw_ti = RawTypeInformation(dpcode="r", type_data="", report_type=None)
    assert raw_ti.read_device_value(_fake_device(status={"r": "aGVsbG8="})) == b"hello"

    str_ti = StringTypeInformation(dpcode="s", type_data="", report_type=None)
    assert str_ti.read_device_value(_fake_device(status={"s": "abc"})) == "abc"


def test_find_dpcode_prefers_status_range_unless_prefer_function():
    device = _fake_device(
        status_range={"sw": _enum_spec({"0": "a"})},
        function={"sw": _enum_spec({"0": "b"})},
    )
    ti = EnumTypeInformation.find_dpcode(device, "sw")
    assert ti.range == ["a"]
    ti = EnumTypeInformation.find_dpcode(device, "sw", prefer_function=True)
    assert ti.range == ["b"]


def test_dpcode_boolean_wrapper_read_and_write():
    device = _fake_device(
        status_range={"sw": {"type": DPType.BOOLEAN, "values": ""}},
        status={"sw": True},
    )
    wrapper = DPCodeBooleanWrapper.find_dpcode(device, "sw")
    assert wrapper is not None
    assert wrapper.read_device_status(device) is True
    assert wrapper.get_update_commands(device, False) == [
        {"code": "sw", "dp_id": None, "value": False}
    ]


def test_dpcode_enum_wrapper_exposes_options():
    device = _fake_device(status_range={"m": _enum_spec({"0": "a", "1": "b"})})
    wrapper = DPCodeEnumWrapper.find_dpcode(device, "m")
    assert wrapper is not None
    assert wrapper.options == ["a", "b"]
    with pytest.raises(SetValueOutOfRangeError):
        wrapper.get_update_commands(device, "zzz")


def test_dpcode_integer_wrapper_bounds():
    device = _fake_device(
        status_range={"temp": _int_spec(min=0, max=300, scale=1, step=1)}
    )
    wrapper = DPCodeIntegerWrapper.find_dpcode(device, "temp")
    assert wrapper is not None
    assert wrapper.min_value == 0
    assert wrapper.max_value == 30
    assert wrapper.value_step == 0.1
    assert wrapper.get_update_commands(device, 25.5) == [
        {"code": "temp", "dp_id": None, "value": 255}
    ]


def test_wrapper_skip_update():
    wrapper = DPCodeBooleanWrapper("sw", BooleanTypeInformation(dpcode="sw", type_data="", report_type=None))
    assert wrapper.skip_update(None, []) is True
    assert wrapper.skip_update(None, ["sw"]) is False


def test_dp_wrapper_by_code_and_by_id():
    device = _fake_device(
        status_range={
            "work_mode": {**_enum_spec({"0": "color", "1": "white"}), "dp_id": 2},
            "bright": {**_int_spec(min=0, max=1000, scale=0, step=1), "dp_id": 3},
        }
    )
    enum_wrapper = dp_wrapper_by_code(device, "work_mode")
    assert isinstance(enum_wrapper, DPCodeEnumWrapper)
    assert enum_wrapper.dp_id == 2

    int_wrapper = dp_wrapper_by_id(device, 3)
    assert isinstance(int_wrapper, DPCodeIntegerWrapper)
    assert int_wrapper.dpcode == "bright"
    assert dp_wrapper_by_id(device, 999) is None


def test_dp_wrapper_by_id_accepts_string_dp_id():
    """Entity configs pass dp_id as str; BLE specs store int. Both must resolve."""
    device = _fake_device(
        status_range={"bright": {**_int_spec(min=0, max=1000), "dp_id": 3}}
    )
    wrapper = dp_wrapper_by_id(device, "3")
    assert isinstance(wrapper, DPCodeIntegerWrapper)
    assert wrapper.dpcode == "bright"
    assert wrapper.dp_id == "3"


def test_dp_wrapper_by_id_prefers_status_range():
    device = _fake_device(
        status_range={"work_mode": {**_enum_spec({"0": "color"}), "dp_id": 2}},
        function={"work_mode": {**_enum_spec({"0": "music"}), "dp_id": 2}},
    )
    wrapper = dp_wrapper_by_id(device, 2)
    assert wrapper.options == ["color"]


def test_tuya_device_dp_type_and_status_surface_ble():
    """BLE device: function/status_range passthrough + dpcode status."""
    ble = SimpleNamespace(
        function={
            "work_mode": SimpleNamespace(
                code="work_mode", dp_id=2, type=DPType.ENUM, values={"0": "color", "1": "white"}
            )
        },
        status_range={},
        status={"work_mode": "color"},
    )
    tuya_device = object.__new__(TuyaDevice)
    tuya_device._interface = SimpleNamespace(ble_device=ble)
    tuya_device._device_config = SimpleNamespace(transport="ble")
    tuya_device._status = {"2": "color"}

    assert tuya_device.function["work_mode"].dp_id == 2
    assert tuya_device.status["work_mode"] == "color"
    ti = tuya_device.dp_type("work_mode")
    assert isinstance(ti, EnumTypeInformation)
    assert ti.range == ["color", "white"]
    assert tuya_device.dp_type("nope") is None


def test_tuya_device_spec_surface_ethernet():
    """Ethernet device: specs + dpcode status derived from cloud dps_data."""
    tuya_device = object.__new__(TuyaDevice)
    tuya_device.id = "dev1"
    tuya_device._interface = None
    tuya_device._status = {"1": True, "2": "color"}
    tuya_device._hass_entry = SimpleNamespace(
        cloud_data=SimpleNamespace(
            device_list={
                "dev1": {
                    "dps_data": {
                        "1": {"code": "switch", "type": DPType.BOOLEAN, "values": ""},
                        "2": {"code": "work_mode", "type": DPType.ENUM, "values": {"0": "color"}},
                    }
                }
            }
        )
    )

    assert tuya_device.function["switch"]["type"] == DPType.BOOLEAN
    assert tuya_device.status["switch"] is True
    assert tuya_device.status["work_mode"] == "color"
    assert isinstance(tuya_device.dp_type("work_mode"), EnumTypeInformation)
    assert tuya_device.dp_type("switch") is not None