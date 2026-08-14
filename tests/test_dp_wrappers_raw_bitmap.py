"""Tests for localtuya-only DP wrappers (RawDPWrapper + BitmapMaskWrapper).

RawDPWrapper is the spec-less fallback used when an entity's DP id has no
cloud spec; BitmapMaskWrapper applies a configured bitmask on top of any
inner wrapper (cloud spec or raw). Both live in core/dp_wrappers.py.
"""

from types import SimpleNamespace

from custom_components.localtuya.core.dp_wrappers import (
    BitmapMaskWrapper,
    RawDPWrapper,
)


def _fake_device(status=None):
    """Build a duck-typed status surface like core's CustomerDevice."""
    return SimpleNamespace(status=status or {})


def _raw_wrapper(dp_id):
    return RawDPWrapper(dp_id)


class _InnerWrapper:
    def __init__(self, dpcode="switch", dp_id=1, skip_result=False):
        self.dpcode = dpcode
        self.dp_id = dp_id
        self.skip_result = skip_result
        self.skipped_with = None

    def skip_update(self, device, updated_status_properties, dp_timestamps=None):
        self.skipped_with = (updated_status_properties, dp_timestamps)
        return self.skip_result


def test_raw_wrapper_identity():
    """dpcode and dp_id mirror the numeric DP id (str key)."""
    wrapper = _raw_wrapper(5)
    assert wrapper.dpcode == "5"
    assert wrapper.dp_id == 5


def test_raw_wrapper_reads_raw_dp_value():
    """Reads device.status by str(dp_id) without conversion."""
    device = _fake_device(status={"3": b"\x01\x02"})
    wrapper = _raw_wrapper(3)
    assert wrapper.read_device_status(device) == b"\x01\x02"


def test_raw_wrapper_missing_value_returns_none():
    """Missing DP value reads None like any status lookup."""
    device = _fake_device(status={})
    assert _raw_wrapper(3).read_device_status(device) is None


def test_raw_wrapper_write_passthrough():
    """get_update_commands sends the value unchanged with dp_id/str dpcode."""
    device = _fake_device(status={"3": False})
    wrapper = _raw_wrapper(3)
    assert wrapper.get_update_commands(device, True) == [
        {"code": "3", "dp_id": 3, "value": True}
    ]


def test_raw_wrapper_never_skips():
    """Spec-less DP always reflects device state (skip_update False)."""
    assert _raw_wrapper(3).skip_update(None, []) is False
    assert _raw_wrapper(3).skip_update(None, ["3"]) is False


def test_raw_wrapper_number_bounds_are_none():
    """Unknown spec means no min/max/step; entities fall back to config."""
    wrapper = _raw_wrapper(3)
    assert wrapper.min_value is None
    assert wrapper.max_value is None
    assert wrapper.value_step is None


def test_bitmap_wrapper_copies_inner_identity():
    """dpcode/dp_id come from the wrapped inner wrapper."""
    wrapper = BitmapMaskWrapper(_InnerWrapper(dpcode="switch", dp_id=1), b"\x01")
    assert wrapper.dpcode == "switch"
    assert wrapper.dp_id == 1


def test_bitmap_wrapper_read_bit_set():
    """read_device_status True when any masked bit is set."""
    wrapper = BitmapMaskWrapper(_InnerWrapper(), b"\x02")
    assert wrapper.read_device_status(_fake_device(status={"1": b"\x00"})) is False
    assert wrapper.read_device_status(_fake_device(status={"1": b"\x02"})) is True
    # Unrelated bits do not trigger the mask.
    assert wrapper.read_device_status(_fake_device(status={"1": b"\x01"})) is False


def test_bitmap_wrapper_read_multibyte_mask():
    """Mask with multiple bytes ANDs each byte with its mask byte."""
    wrapper = BitmapMaskWrapper(_InnerWrapper(dp_id=1), b"\x01\x04")
    assert wrapper.read_device_status(_fake_device(status={"1": b"\x01\x00"})) is True
    assert wrapper.read_device_status(_fake_device(status={"1": b"\x00\x04"})) is True
    assert wrapper.read_device_status(_fake_device(status={"1": b"\x00\x00"})) is False


def test_bitmap_wrapper_read_pads_short_value():
    """Shorter raw value is zero-padded to mask length before matching."""
    wrapper = BitmapMaskWrapper(_InnerWrapper(dp_id=1), b"\x01\x00")
    assert wrapper.read_device_status(_fake_device(status={"1": b"\x01"})) is True
    wrapper = BitmapMaskWrapper(_InnerWrapper(dp_id=1), b"\x00\x01")
    assert wrapper.read_device_status(_fake_device(status={"1": b"\x01"})) is False


def test_bitmap_wrapper_read_truncates_long_value():
    """Longer raw value is truncated to mask length."""
    wrapper = BitmapMaskWrapper(_InnerWrapper(dp_id=1), b"\x01")
    assert wrapper.read_device_status(_fake_device(status={"1": b"\x01\x02"})) is True


def test_bitmap_wrapper_read_non_bytes_is_off():
    """Non-bytes status (int, str, missing) is treated as all-zero."""
    wrapper = BitmapMaskWrapper(_InnerWrapper(dp_id=1), b"\x01")
    assert wrapper.read_device_status(_fake_device(status={"1": 1})) is False
    assert wrapper.read_device_status(_fake_device(status={"1": "x"})) is False
    assert wrapper.read_device_status(_fake_device(status={})) is False


def test_bitmap_wrapper_write_sets_bit():
    """Turning on ORs the mask into the current value."""
    wrapper = BitmapMaskWrapper(_InnerWrapper(dp_id=1), b"\x01")
    device = _fake_device(status={"1": b"\x00"})
    assert wrapper.get_update_commands(device, True) == [
        {"code": "switch", "dp_id": 1, "value": b"\x01"}
    ]


def test_bitmap_wrapper_write_clears_bit():
    """Turning off ANDs the complement of the mask into the current value."""
    wrapper = BitmapMaskWrapper(_InnerWrapper(dp_id=1), b"\x02")
    device = _fake_device(status={"1": b"\x03"})
    assert wrapper.get_update_commands(device, False) == [
        {"code": "switch", "dp_id": 1, "value": b"\x01"}
    ]


def test_bitmap_wrapper_write_preserves_unrelated_bits():
    """Only masked bits change on write; the rest of the byte survives."""
    wrapper = BitmapMaskWrapper(_InnerWrapper(dp_id=1), b"\x04")
    device = _fake_device(status={"1": b"\x0b"})  # 1011
    assert wrapper.get_update_commands(device, True) == [
        {"code": "switch", "dp_id": 1, "value": b"\x0f"}
    ]
    assert wrapper.get_update_commands(device, False) == [
        {"code": "switch", "dp_id": 1, "value": b"\x0b"}
    ]


def test_bitmap_wrapper_write_multibyte():
    """Multi-byte mask writes each byte independently."""
    wrapper = BitmapMaskWrapper(_InnerWrapper(dp_id=1), b"\x01\x08")
    device = _fake_device(status={"1": b"\x00\x00"})
    assert wrapper.get_update_commands(device, True) == [
        {"code": "switch", "dp_id": 1, "value": b"\x01\x08"}
    ]
    assert wrapper.get_update_commands(device, False) == [
        {"code": "switch", "dp_id": 1, "value": b"\x00\x00"}
    ]


def test_bitmap_wrapper_skip_update_delegates():
    """Skip decisions are delegated to the inner wrapper."""
    inner = _InnerWrapper(skip_result=True)
    wrapper = BitmapMaskWrapper(inner, b"\x01")
    assert wrapper.skip_update(_fake_device(), ["switch"]) is True
    assert inner.skipped_with == (["switch"], None)

    inner = _InnerWrapper(skip_result=False)
    wrapper = BitmapMaskWrapper(inner, b"\x01")
    assert wrapper.skip_update(_fake_device(), []) is False