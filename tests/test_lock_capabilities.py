"""Checks for lock_capabilities.discover.

Ported from ha_tuya_ble tests/test_lock_capabilities.py (commit bea2520).
Pins three product specifications captured from real devices, plus the two
ways a lock can end up with no specification at all.
"""

from __future__ import annotations

from dataclasses import dataclass

from custom_components.localtuya.core.tuya_ble_lib import lock_capabilities


@dataclass
class FakeSpec:
    """Stands in for the cloud specification entry of one datapoint."""

    dp_id: int


class FakeDevice:
    """Only the three attributes discovery reads."""

    def __init__(self, product_id: str, function: dict, status_range: dict) -> None:
        self.address = "AA:BB:CC:DD:EE:FF"
        self.product_id = product_id
        self.function = {code: FakeSpec(dp) for code, dp in function.items()}
        self.status_range = {code: FakeSpec(dp) for code, dp in status_range.items()}


# The write side lives in function and the reporting side in status_range,
# exactly as the cloud returns it.
SPEC_0QXP5U7S_FUNCTION = {
    "unlock_method_create": 1,
    "unlock_method_delete": 2,
    "synch_method": 54,
    "automatic_lock": 33,
}
SPEC_0QXP5U7S_STATUS = {
    "unlock_fingerprint": 12,
    "unlock_ble": 19,
    "unlock_phone_remote": 62,
    "unlock_voice_remote": 63,
    "lock_motor_state": 47,
    "synch_method": 54,
}

# From the specification quoted in ha_tuya_ble issue #1713, for a lock with
# no entry in FALLBACK_CAPABILITIES.
SPEC_ISK2P555_FUNCTION = {
    "unlock_method_create": 1,
    "unlock_method_delete": 2,
    "synch_method": 54,
}
SPEC_ISK2P555_STATUS = {
    "unlock_fingerprint": 12,
    "unlock_password": 13,
    "unlock_dynamic": 14,
    "unlock_temporary": 55,
    "unlock_ble": 19,
    "unlock_phone_remote": 62,
    "unlock_voice_remote": 63,
    "unlock_offline_pd": 67,
}


def test_lock_with_hand_written_fallback():
    found = lock_capabilities.discover(
        FakeDevice("0qxp5u7s", SPEC_0QXP5U7S_FUNCTION, SPEC_0QXP5U7S_STATUS)
    )
    assert found.credential_add_dp_id == 1
    assert found.credential_delete_dp_id == 2
    assert found.credential_sync_dp_id == 54
    assert found.unlock_records == {
        12: "fingerprint",
        19: "bluetooth",
        62: "remote",
        63: "voice",
    }
    assert found.manages_credentials is True
    assert found.reports_unlocks is True
    assert found == lock_capabilities.FALLBACK_CAPABILITIES["0qxp5u7s"]


def test_lock_discovered_from_specification_alone():
    found = lock_capabilities.discover(
        FakeDevice("isk2p555", SPEC_ISK2P555_FUNCTION, SPEC_ISK2P555_STATUS)
    )
    assert found.credential_add_dp_id == 1
    assert found.credential_delete_dp_id == 2
    assert found.credential_sync_dp_id == 54
    assert found.unlock_records == {
        12: "fingerprint",
        13: "password",
        14: "dynamic_password",
        55: "temporary_password",
        19: "bluetooth",
        62: "remote",
        63: "voice",
        67: "offline_password",
    }


def test_no_specification_at_all():
    # A known product still falls back to the measured datapoints.
    assert (
        lock_capabilities.discover(FakeDevice("0qxp5u7s", {}, {}))
        == lock_capabilities.FALLBACK_CAPABILITIES["0qxp5u7s"]
    )
    bare = lock_capabilities.discover(FakeDevice("unknown_lock", {}, {}))
    assert bare == lock_capabilities.TuyaBLELockCapabilities()
    assert bare.manages_credentials is False


def test_device_that_is_not_a_lock():
    fingerbot = lock_capabilities.discover(
        FakeDevice(
            "blliqpsj",
            {"mode": 8, "click_sustain_time": 10},
            {"battery_percentage": 12},
        )
    )
    assert fingerbot.manages_credentials is False
    assert fingerbot.unlock_records == {}


def test_fallback_table_not_handed_out_to_be_mutated():
    first = lock_capabilities.discover(FakeDevice("0qxp5u7s", {}, {}))
    first.unlock_records[99] = "nonsense"
    second = lock_capabilities.discover(FakeDevice("0qxp5u7s", {}, {}))
    assert second.unlock_records == {
        12: "fingerprint",
        19: "bluetooth",
        62: "remote",
        63: "voice",
    }
