"""Unit tests for the composable DP wrapper decorators.

Each decorator wraps a RawDPWrapper and owns one conversion step, so these
tests verify read (raw -> HA) and write (HA -> raw) through the public
``read_device_status`` / ``get_update_commands`` interface.
"""

import base64
from types import SimpleNamespace

import pytest

from custom_components.localtuya.const import DictSelector
from custom_components.localtuya.core.dp_wrappers import RawDPWrapper
from custom_components.localtuya.core.dp_wrapper_decorators import (
    Base64Utf8RawEventWrapper,
    Base64Utf8StringEventWrapper,
    BinarySensorWrapper,
    BrightnessWrapper,
    ClimateTempWrapper,
    ColorTempWrapper,
    DictSelectorWrapper,
    FanDirectionWrapper,
    FanSpeedPercentageWrapper,
    HumidityCoefficientWrapper,
    InversionWrapper,
    InvertedBooleanWrapper,
    InvertedPercentageWrapper,
    PercentageWrapper,
    ScalingIntegerWrapper,
    SimpleEventEnumWrapper,
    StringColorWrapper,
    TimedCoverMathWrapper,
)


def _device(status: dict) -> SimpleNamespace:
    return SimpleNamespace(status=status)


def _raw(dp_id: str = "1") -> RawDPWrapper:
    return RawDPWrapper(dp_id)


def test_dict_selector_wrapper_read_write_and_options():
    wrapper = DictSelectorWrapper(_raw(), DictSelector({"a": "A", "b": "B"}))
    assert wrapper.options == ["A", "B"]
    assert wrapper.read_device_status(_device({"1": "a"})) == "A"
    assert wrapper.read_device_status(_device({})) is None
    cmds = wrapper.get_update_commands(_device({"1": "a"}), "B")
    assert cmds == [{"code": "1", "dp_id": "1", "value": "b"}]


def test_dict_selector_wrapper_custom_default():
    wrapper = DictSelectorWrapper(
        _raw(), DictSelector({"a": "A"}), default="unknown"
    )
    assert wrapper.read_device_status(_device({"1": "zzz"})) == "unknown"


def test_dict_selector_wrapper_bypasses_inner_enum_validation():
    """The raw value is mapped even when the inner wrapper rejects it.

    The cloud enum range can be wrong (e.g. ``relay_status`` reports ``on``
    while the spec declares ``power_on``); the DictSelector is authoritative,
    so the raw value must be mapped directly instead of being dropped by the
    inner ``EnumTypeInformation``.
    """
    inner = _raw()
    inner.read_device_status = lambda device: None  # simulate enum range mismatch
    wrapper = DictSelectorWrapper(inner, DictSelector({"on": "ON", "off": "OFF"}))
    assert wrapper.read_device_status(_device({"1": "on"})) == "ON"
    cmds = wrapper.get_update_commands(_device({"1": "on"}), "OFF")
    assert cmds == [{"code": "1", "dp_id": "1", "value": "off"}]


def test_scaling_integer_wrapper():
    wrapper = ScalingIntegerWrapper(_raw(), scale=0.1, min_value=0, max_value=30)
    assert wrapper.read_device_status(_device({"1": 255})) == 25.5
    cmds = wrapper.get_update_commands(_device({"1": 255}), 25.5)
    assert cmds[0]["value"] == 255


def test_percentage_wrapper():
    wrapper = PercentageWrapper(_raw())
    assert wrapper.min_value == 0 and wrapper.max_value == 100
    assert wrapper.read_device_status(_device({"1": 42})) == 42
    assert wrapper.get_update_commands(_device({}), 42)[0]["value"] == 42


def test_inverted_percentage_wrapper():
    wrapper = InvertedPercentageWrapper(_raw())
    assert wrapper.read_device_status(_device({"1": 20})) == 80
    assert wrapper.get_update_commands(_device({}), 80)[0]["value"] == 20


def test_inversion_wrapper():
    wrapper = InversionWrapper(_raw(), max_value=100)
    assert wrapper.read_device_status(_device({"1": 0})) == 100
    assert wrapper.get_update_commands(_device({}), 0)[0]["value"] == 100


def test_timed_cover_math_wrapper():
    wrapper = TimedCoverMathWrapper(_raw())
    assert wrapper.read_device_status(_device({"1": 50})) == round(50 * 65535 / 100)
    raw = wrapper.get_update_commands(_device({}), 50)[0]["value"]
    assert raw == round(50 * 100 / 65535)


def test_inverted_boolean_wrapper():
    wrapper = InvertedBooleanWrapper(_raw())
    assert wrapper.read_device_status(_device({"1": True})) is False
    assert wrapper.get_update_commands(_device({}), True)[0]["value"] is False


def test_binary_sensor_wrapper_matches_on_values():
    wrapper = BinarySensorWrapper(_raw(), "alarm")
    assert wrapper.read_device_status(_device({"1": "alarm"})) is True
    assert wrapper.read_device_status(_device({"1": "normal"})) is False
    assert wrapper.read_device_status(_device({})) is None


def test_binary_sensor_wrapper_default_on_values():
    """Default on-values cover the common bool/string/int encodings."""
    wrapper = BinarySensorWrapper(_raw())
    assert wrapper.read_device_status(_device({"1": True})) is True
    assert wrapper.read_device_status(_device({"1": "pir"})) is True
    assert wrapper.read_device_status(_device({"1": 1})) is True
    assert wrapper.read_device_status(_device({"1": 0})) is False
    assert wrapper.read_device_status(_device({"1": "off"})) is False


def test_simple_event_enum_wrapper():
    inner = SimpleNamespace(
        dpcode="switch_mode1",
        options=["single_click", "double_click"],
        read_device_status=lambda device: device.status.get("switch_mode1"),
    )
    wrapper = SimpleEventEnumWrapper(inner)
    assert wrapper.options == ["single_click", "double_click"]
    assert wrapper.read_device_status(
        _device({"switch_mode1": "double_click"})
    ) == ("double_click", None)
    assert wrapper.read_device_status(_device({})) is None


def test_base64_utf8_string_event_wrapper():
    inner = SimpleNamespace(
        dpcode="alarm_message",
        read_device_status=lambda device: device.status.get("alarm_message"),
    )
    wrapper = Base64Utf8StringEventWrapper(inner)
    assert wrapper.options == ["triggered"]
    encoded = base64.b64encode(b"hello").decode("ascii")
    assert wrapper.read_device_status(_device({"alarm_message": encoded})) == (
        "triggered",
        {"message": "hello"},
    )


def test_base64_utf8_raw_event_wrapper():
    inner = SimpleNamespace(
        dpcode="doorbell_pic",
        read_device_status=lambda device: device.status.get("doorbell_pic"),
    )
    wrapper = Base64Utf8RawEventWrapper(inner)
    assert wrapper.options == ["triggered"]
    assert wrapper.read_device_status(_device({"doorbell_pic": b"hello"})) == (
        "triggered",
        {"message": "hello"},
    )


def test_climate_temp_wrapper_precision_and_unit_convert():
    f_to_c = lambda v: (v - 32) * 5 / 9
    c_to_f = lambda v: (v * 1.8) + 32
    wrapper = ClimateTempWrapper(
        _raw(), precision=1.0, unit_from=f_to_c, unit_to=c_to_f
    )
    assert wrapper.read_device_status(_device({"1": 68})) == pytest.approx(20.0)
    assert wrapper.get_update_commands(_device({}), 20.0)[0]["value"] == 68


def test_humidity_coefficient_wrapper():
    wrapper = HumidityCoefficientWrapper(_raw(), coefficient=2.0)
    assert wrapper.read_device_status(_device({"1": 100})) == 50
    assert wrapper.get_update_commands(_device({}), 50)[0]["value"] == 100


def test_fan_speed_percentage_wrapper_ranged():
    wrapper = FanSpeedPercentageWrapper(_raw(), speed_range=(1, 6))
    assert wrapper.read_device_status(_device({"1": 4})) == 66
    assert wrapper.get_update_commands(_device({}), 100)[0]["value"] == 6


def test_fan_speed_percentage_wrapper_ordered_list():
    wrapper = FanSpeedPercentageWrapper(
        _raw(), speed_range=(1, 6), ordered_list=["low", "mid", "high"]
    )
    assert wrapper.read_device_status(_device({"1": "mid"})) == 66
    assert wrapper.get_update_commands(_device({}), 100)[0]["value"] == "high"


def test_fan_direction_wrapper():
    wrapper = FanDirectionWrapper(_raw(), forward_value="fwd", reverse_value="rev")
    assert wrapper.read_device_status(_device({"1": "fwd"})) == "forward"
    assert wrapper.read_device_status(_device({"1": "rev"})) == "reverse"
    assert wrapper.read_device_status(_device({"1": "zzz"})) is None
    assert wrapper.get_update_commands(_device({}), "reverse")[0]["value"] == "rev"


def test_brightness_wrapper():
    wrapper = BrightnessWrapper(_raw(), lower=0, upper=1000)
    assert wrapper.read_device_status(_device({"1": 500})) == 128
    assert wrapper.get_update_commands(_device({}), 255)[0]["value"] == 1000


def test_color_temp_wrapper():
    wrapper = ColorTempWrapper(_raw(), 2700, 6500, 0, 1000)
    assert wrapper.read_device_status(_device({"1": 0})) == 2700
    assert wrapper.get_update_commands(_device({}), 6500)[0]["value"] == 1000


def test_string_color_wrapper_v2_roundtrip():
    wrapper = StringColorWrapper(_raw(), None, upper_brightness=1000)
    encoded = wrapper.encode(4, 100.0, 128)
    assert encoded == "000403e801f6"
    assert wrapper.decode(encoded) == (4, 100.0, 128)


def test_string_color_wrapper_rgb_encoded_decode():
    wrapper = StringColorWrapper(_raw(), None, upper_brightness=1000)
    hue, sat, value = wrapper.decode("0319090087db1c")
    assert hue == 135
    assert sat == pytest.approx(219 * 100 / 255)
    # v1/rgb-encoded value field is already on the 0..255 scale.
    assert value == 28


def test_string_color_wrapper_rgb_encoded_roundtrip():
    wrapper = StringColorWrapper(_raw(), None, upper_brightness=1000)
    encoded = wrapper.encode(135, 100.0, 28, current="0319090087db1c")
    hue, sat, value = wrapper.decode(encoded)
    assert hue == 135
    assert sat == 100.0
    assert value == 28


def test_string_color_wrapper_base64_roundtrip():
    wrapper = StringColorWrapper(_raw(), None, upper_brightness=1000, use_raw=True)
    encoded = wrapper.encode(135, 219, 128)
    hue, sat, value = wrapper.decode(encoded)
    assert hue == 135
    assert sat == 219
    assert value == 128


def test_decorator_composition():
    """Decorators compose via the public interface."""
    wrapper = InversionWrapper(TimedCoverMathWrapper(_raw()), max_value=100)
    assert wrapper.read_device_status(_device({"1": 50})) == 100 - round(
        50 * 65535 / 100
    )
    raw = wrapper.get_update_commands(_device({}), 25)[0]["value"]
    assert raw == round((100 - 25) * 100 / 65535)


def test_decorator_skip_update_delegates():
    # RawDPWrapper has no dpcode to compare, so it never skips; the decorator
    # inherits that behaviour through delegation.
    wrapper = DictSelectorWrapper(_raw(), DictSelector({"a": "A"}))
    assert wrapper.skip_update(_device({}), ["1"]) is False
    assert wrapper.skip_update(_device({}), ["2"]) is False
