"""Test for localtuya quirks registry."""

from custom_components.localtuya.core.quirks import (
    FINGERBOT_SWITCH_DP,
    QUIRKS_REGISTRY,
    DeviceQuirk,
    QuirksRegistry,
)


def test_quirk_registry_populated_from_fingerbot_table():
    assert len(QUIRKS_REGISTRY._quirks) == len(FINGERBOT_SWITCH_DP)
    assert len(QUIRKS_REGISTRY._quirks) > 0


def test_get_quirk_for_device_matches_product_id():
    for product_id, dp_id in FINGERBOT_SWITCH_DP.items():
        quirk = QUIRKS_REGISTRY.get_quirk_for_device(type("Dev", (), {"product_id": product_id})())
        assert quirk is not None
        assert quirk.button_switch_dp == dp_id


def test_get_quirk_for_device_unknown_product():
    assert QUIRKS_REGISTRY.get_quirk_for_device(type("Dev", (), {"product_id": "unknown"})()) is None


def test_get_quirk_for_device_missing_product_id():
    assert QUIRKS_REGISTRY.get_quirk_for_device(type("Dev", (), {})()) is None


def test_custom_register_overrides():
    registry = QuirksRegistry()
    registry.register("abc", DeviceQuirk(button_switch_dp=5))
    quirk = registry.get_quirk_for_device(type("Dev", (), {"product_id": "abc"})())
    assert quirk is not None
    assert quirk.button_switch_dp == 5
