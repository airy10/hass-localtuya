"""Test for localtuya quirks registry."""

from custom_components.localtuya.const import DPType
from custom_components.localtuya.core.dp_wrappers import dp_wrapper_by_code
from custom_components.localtuya.core.quirks import (
    DPMode,
    FINGERBOT_SWITCH_DP,
    QUIRKS_REGISTRY,
    DeviceQuirk,
    QuirksRegistry,
)


def test_quirk_registry_populated_from_fingerbot_table():
    for product_id, dp_id in FINGERBOT_SWITCH_DP.items():
        quirk = QUIRKS_REGISTRY.get_quirk_for_device(
            type("Dev", (), {"product_id": product_id})()
        )
        assert quirk is not None
        assert quirk.button_switch_dp == dp_id


def test_get_quirk_for_device_unknown_product():
    assert (
        QUIRKS_REGISTRY.get_quirk_for_device(
            type("Dev", (), {"product_id": "unknown"})()
        )
        is None
    )


def test_get_quirk_for_device_missing_product_id():
    assert QUIRKS_REGISTRY.get_quirk_for_device(type("Dev", (), {})()) is None


def test_custom_register_overrides():
    registry = QuirksRegistry()
    registry.register("abc", DeviceQuirk(button_switch_dp=5))
    quirk = registry.get_quirk_for_device(type("Dev", (), {"product_id": "abc"})())
    assert quirk is not None
    assert quirk.button_switch_dp == 5


def test_ported_spec_quirks_registered():
    for product_id in (
        "dft4ebatvon3ha5s",  # bh kettle
        "b9oa3zocv4qq47iy",  # cl tubular motor
        "uhtamgih7kkdcqtx",  # cs dehumidifier
        "eyEYwtdx9VhexxLW",  # cz socket
        "xwv3jifdbhbolgh3",  # fs tower fan
        "hw50w7qvxluhslkk",  # kt mini-split
        "p6sqiuesvhmhvv4f",  # tdq contact sensor
        "cpmgn2cf",  # wk thermostat
        "m7kacaxrxbxeegfs",  # wsdcg sensor
        "7bqwya0ydtz4q3ss",  # znnbq inverter
    ):
        quirk = QUIRKS_REGISTRY.get_quirk_for_device(
            type("Dev", (), {"product_id": product_id})()
        )
        assert quirk is not None, product_id


def test_add_dpid_enum_patches_both_surfaces():
    quirk = (
        DeviceQuirk()
        .applies_to(product_id="x")
        .add_dpid_enum(
            dpid=4,
            dpcode="mode",
            dpmode=DPMode.READ | DPMode.WRITE,
            enum_range=["a", "b"],
        )
    )
    patched_status = quirk.patch_status_range({})
    patched_function = quirk.patch_function({})
    assert patched_status["mode"]["type"] == DPType.ENUM
    assert patched_status["mode"]["values"] == {"range": ["a", "b"]}
    assert patched_status["mode"]["dp_id"] == 4
    assert patched_function["mode"]["type"] == DPType.ENUM


def test_read_only_dp_only_lands_in_status_range():
    quirk = (
        DeviceQuirk()
        .applies_to(product_id="x")
        .add_dpid_integer(
            dpid=3,
            dpcode="humidity",
            dpmode=DPMode.READ,
            unit="%",
            min=0,
            max=100,
            scale=0,
            step=1,
        )
    )
    assert "humidity" in quirk.patch_status_range({})
    assert "humidity" not in quirk.patch_function({})


def test_remove_dpid_drops_from_both_surfaces():
    quirk = (
        DeviceQuirk()
        .applies_to(product_id="x")
        .remove_dpid(dpid=3, dpcode="percent_state")
    )
    assert quirk.patch_status_range({"percent_state": {}, "other": {}}) == {"other": {}}
    assert quirk.patch_function({"percent_state": {}, "other": {}}) == {"other": {}}


def test_override_category():
    quirk = DeviceQuirk().applies_to(product_id="x").override_category("mcs")
    assert quirk.patched_category("tdq") == "mcs"
    assert DeviceQuirk().patched_category("tdq") == "tdq"


def test_kettle_quirk_resolves_via_dp_wrapper():
    quirk = QUIRKS_REGISTRY.get_quirk_for_device(
        type("Dev", (), {"product_id": "dft4ebatvon3ha5s"})()
    )

    class FakeDevice:
        def __init__(self):
            self.function = quirk.patch_function({})
            self.status_range = quirk.patch_status_range({})

    wrapper = dp_wrapper_by_code(FakeDevice(), "temp_setting_quick_c")
    assert wrapper is not None
    assert wrapper.options == ["80", "85", "90", "95", "100"]


def test_socket_quirk_scales_power():
    quirk = QUIRKS_REGISTRY.get_quirk_for_device(
        type("Dev", (), {"product_id": "eyEYwtdx9VhexxLW"})()
    )
    spec = quirk.patch_status_range({})["cur_power"]
    assert spec["values"]["scale"] == 1
    assert spec["values"]["unit"] == "W"


QUIRK_FILE = (
    "from custom_components.localtuya.core.quirks import DPMode, QUIRKS_REGISTRY, DeviceQuirk\n"
    "DeviceQuirk().applies_to(product_id='customtestprod')"
    ".add_dpid_boolean(\n"
    "    dpid=1, dpcode='power', dpmode=DPMode.READ | DPMode.WRITE\n"
    ").register(QUIRKS_REGISTRY)\n"
)


def _lookup_custom():
    return QUIRKS_REGISTRY.get_quirk_for_device(
        type("Dev", (), {"product_id": "customtestprod"})()
    )


def test_load_custom_quirks_registers_and_purges_on_reload(tmp_path):
    quirk_dir = tmp_path / "localtuya_quirks"
    quirk_dir.mkdir()
    (quirk_dir / "my_quirk.py").write_text(QUIRK_FILE, encoding="utf-8")

    try:
        assert QUIRKS_REGISTRY.load_custom_quirks(str(quirk_dir)) == 1
        assert _lookup_custom() is not None

        # Deleting the file and reloading must drop the quirk.
        (quirk_dir / "my_quirk.py").unlink()
        assert QUIRKS_REGISTRY.load_custom_quirks(str(quirk_dir)) == 0
        assert _lookup_custom() is None
    finally:
        # Never leak the custom quirk into the shared global registry.
        QUIRKS_REGISTRY._custom_products.clear()
        QUIRKS_REGISTRY._quirks.pop("customtestprod", None)


def test_load_custom_quirks_missing_dir_is_noop(tmp_path):
    before = dict(QUIRKS_REGISTRY._quirks)
    assert QUIRKS_REGISTRY.load_custom_quirks(str(tmp_path / "nope")) == 0
    assert QUIRKS_REGISTRY._quirks == before


def test_load_custom_quirks_broken_module_does_not_raise(tmp_path):
    quirk_dir = tmp_path / "localtuya_quirks"
    quirk_dir.mkdir()
    (quirk_dir / "broken.py").write_text(
        "raise RuntimeError('boom')\n", encoding="utf-8"
    )
    assert QUIRKS_REGISTRY.load_custom_quirks(str(quirk_dir)) == 0
