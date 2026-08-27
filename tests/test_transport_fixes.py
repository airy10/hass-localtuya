"""Regression tests for the BLE transport review fixes."""

import asyncio
import logging
import struct
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from bleak_retry_connector import BleakError

from custom_components.localtuya.const import (
    DEVICE_CLOUD_DATA,
    DPType,
    TRANSPORT_BLE,
    TRANSPORT_ETHERNET,
)
from custom_components.localtuya.coordinator import TuyaDevice
from custom_components.localtuya.core.pytuya import MessageDispatcher
from custom_components.localtuya.core.pytuya.const import Affix
from custom_components.localtuya.core import sharing_cloud as sharing_cloud_module
from custom_components.localtuya.core.sharing_cloud import SharingCloud
from custom_components.localtuya.core.transport import (
    BluetoothTransport,
    EthernetTransport,
)
from custom_components.localtuya.core.tuya_ble_lib import TuyaBLEDevice
from custom_components.localtuya.core.tuya_ble_lib.const import TuyaBLECode


class FakeProtocol:
    """Minimal protocol double for the Ethernet adapter."""

    is_connected = True
    dispatched_dps = {1: False}

    def __init__(self):
        self.keep_alive_calls = []
        self.close = AsyncMock()

    def keep_alive(self, *, is_gateway):
        self.keep_alive_calls.append(is_gateway)

    def add_dps_to_request(self, dps):
        self.requested_dps = dps

    async def status(self, *, cid):
        return {1: False}

    async def reset(self, dp_id, *, cid):
        return None

    async def set_dps(self, dps, *, cid):
        self.set_values = (dps, cid)

    async def update_dps(self, *, dps, cid):
        return True

    async def detect_available_dps(self, *, cid):
        return {1: False}

    def enable_debug(self, enable, friendly_name):
        self.debug = (enable, friendly_name)

    def set_updatedps_list(self, dps):
        self.updated_dps = dps


class FakeBleDevice:
    """Minimal BLE device double exposing the callback contract."""

    is_connected = True
    rssi = -42
    status = {"switch": False}
    function = {
        "switch": SimpleNamespace(dp_id=1, type=DPType.BOOLEAN),
    }
    status_range = {}

    def __init__(self):
        self.callbacks = []
        self.connected_callbacks = []
        self.disconnect_callbacks = []
        self.stop_calls = 0
        self.datapoints = SimpleNamespace()

    def register_callback(self, callback):
        self.callbacks.append(callback)

        def unregister():
            self.callbacks.remove(callback)

        return unregister

    def register_connected_callback(self, callback):
        self.connected_callbacks.append(callback)

        def unregister():
            self.connected_callbacks.remove(callback)

        return unregister

    def register_disconnected_callback(self, callback):
        self.disconnect_callbacks.append(callback)

        def unregister():
            self.disconnect_callbacks.remove(callback)

        return unregister

    async def stop(self):
        self.stop_calls += 1


@pytest.mark.asyncio
async def test_ethernet_transport_keep_alive_is_synchronous():
    protocol = FakeProtocol()
    transport = EthernetTransport(protocol)

    transport.keep_alive(is_gateway=True)

    assert protocol.keep_alive_calls == [True]
    assert await transport.status(cid=None) == {1: False}
    assert transport.dispatched_dps == {1: False}


@pytest.mark.asyncio
async def test_ethernet_transport_preserves_unavailable_status():
    protocol = FakeProtocol()
    protocol.status = AsyncMock(return_value=None)
    protocol.detect_available_dps = AsyncMock(return_value=None)
    transport = EthernetTransport(protocol)

    assert await transport.status(cid=None) is None
    assert await transport.detect_available_dps(cid=None) is None


@pytest.mark.asyncio
async def test_bluetooth_transport_forwards_delta_and_disconnect():
    device = FakeBleDevice()
    updates = []
    connected = []
    disconnects = []
    transport = BluetoothTransport(
        device,
        updates.append,
        connected_listener=lambda: connected.append(True),
        disconnect_listener=lambda: disconnects.append(True),
    )

    device.connected_callbacks[0]()
    assert connected == [True]

    device.callbacks[0]([SimpleNamespace(id=1, value=False)])
    assert updates == [{1: False}]
    assert transport.dispatched_dps == {1: False}

    device.disconnect_callbacks[0]()
    assert disconnects == [True]

    await transport.close()
    await transport.close()
    assert device.stop_calls == 1
    assert device.callbacks == []
    assert device.connected_callbacks == []
    assert device.disconnect_callbacks == []


def test_ble_status_range_is_loaded_without_functions():
    device = TuyaBLEDevice(None, SimpleNamespace(address="AA:BB:CC:DD:EE:FF"))

    device.append_functions(
        [],
        [
            {
                "code": "temperature",
                "dp_id": 2,
                "type": DPType.INTEGER,
                "values": '{"min":0}',
            }
        ],
    )

    assert device.status_range["temperature"].dp_id == 2


def test_ble_work_mode_fallback_maps_enum_when_cloud_values_empty():
    device = TuyaBLEDevice(None, SimpleNamespace(address="AA:BB:CC:DD:EE:FF"))
    device.append_functions(
        [
            {
                "code": "work_mode",
                "dp_id": 2,
                "type": DPType.ENUM,
                "values": {},
            },
        ],
        [],
    )

    assert device._enum_string_for_id(2, 0) == "colour"
    assert device._enum_string_for_id(2, 1) == "dynamic_mod"
    assert device._enum_string_for_id(2, 3) == "music"
    assert device._enum_string_for_id(2, 99) is None
    assert device._enum_index_for_id(2, "colour") == 0
    assert device._enum_index_for_id(2, "music") == 3
    assert device._enum_index_for_id(2, "white") == 0


def test_ble_enum_mapping_uses_cloud_values_when_present():
    device = TuyaBLEDevice(None, SimpleNamespace(address="AA:BB:CC:DD:EE:FF"))
    device.append_functions(
        [
            {
                "code": "mode",
                "dp_id": 4,
                "type": DPType.ENUM,
                "values": {"0": "white", "1": "colour", "2": "scene", "3": "music"},
            },
        ],
        [],
    )

    assert device._enum_string_for_id(4, 1) == "colour"
    assert device._enum_index_for_id(4, "scene") == 2


@pytest.mark.asyncio
async def test_ble_write_failure_removes_response_future():
    class FailingClient:
        is_connected = True

        async def write_gatt_char(self, *_args):
            raise BleakError("write failed")

    device = TuyaBLEDevice(None, SimpleNamespace(address="AA:BB:CC:DD:EE:FF"))
    device._client = FailingClient()
    device._build_packets = lambda *_args: [b"packet"]

    with pytest.raises(BleakError):
        await device._send_packet_while_connected(
            TuyaBLECode.FUN_SENDER_DEVICE_STATUS,
            b"",
            0,
            True,
        )

    assert device._input_expected_responses == {}


@pytest.mark.asyncio
async def test_ble_write_cancellation_propagates_and_cleans_future():
    class CancellingClient:
        is_connected = True

        async def write_gatt_char(self, *_args):
            raise asyncio.CancelledError

    device = TuyaBLEDevice(None, SimpleNamespace(address="AA:BB:CC:DD:EE:FF"))
    device._client = CancellingClient()
    device._build_packets = lambda *_args: [b"packet"]

    with pytest.raises(asyncio.CancelledError):
        await device._send_packet_while_connected(
            TuyaBLECode.FUN_SENDER_DEVICE_STATUS,
            b"",
            0,
            True,
        )

    assert device._input_expected_responses == {}


@pytest.mark.asyncio
async def test_ble_late_response_ignores_cancelled_future(monkeypatch):
    loop = asyncio.get_event_loop()
    monkeypatch.setattr(asyncio, "get_running_loop", lambda: loop)
    device = TuyaBLEDevice(None, SimpleNamespace(address="AA:BB:CC:DD:EE:FF"))
    future = asyncio.get_running_loop().create_future()
    future.cancel()
    device._input_expected_responses[7] = future

    device._handle_command_or_response(
        8,
        7,
        TuyaBLECode.FUN_SENDER_DEVICE_STATUS,
        b"\x00",
    )

    assert device._input_expected_responses == {}


@pytest.mark.asyncio
async def test_sharing_cloud_stores_device_dp_metadata():
    function = SimpleNamespace(
        code="switch",
        dp_id=1,
        type=DPType.BOOLEAN,
        values="[true,false]",
    )
    sharing_device = SimpleNamespace(
        function={"switch": function},
        status_range={},
        local_strategy={},
    )
    sharing = object.__new__(SharingCloud)
    sharing._manager = SimpleNamespace(device_map={"device": sharing_device})
    sharing.device_list = {"device": {"id": "device"}}

    dps_data = await sharing.async_get_device_functions("device")

    assert dps_data["1"]["code"] == "switch"
    assert sharing.device_list["device"]["dps_data"] == dps_data


@pytest.mark.asyncio
async def test_sharing_cloud_retries_transient_cache_failure(monkeypatch):
    calls = []

    def flaky_update_device_cache():
        calls.append(1)
        if len(calls) < 3:
            raise RuntimeError("token is expired")

    async def run_job(fn, *args):
        return fn(*args)

    sharing = object.__new__(SharingCloud)
    sharing._hass = SimpleNamespace(async_add_executor_job=run_job)
    manager = SimpleNamespace(update_device_cache=flaky_update_device_cache)
    sleeps = []

    async def fake_sleep(delay):
        sleeps.append(delay)

    monkeypatch.setattr(sharing_cloud_module.asyncio, "sleep", fake_sleep)

    result = await sharing._update_device_cache_with_retry(manager)

    assert result is None
    assert len(calls) == 3
    assert sleeps == [5, 15]


@pytest.mark.asyncio
async def test_sharing_cloud_gives_up_after_final_retry(monkeypatch):
    calls = []

    def dead_update_device_cache():
        calls.append(1)
        raise RuntimeError("token is expired")

    async def run_job(fn, *args):
        return fn(*args)

    sharing = object.__new__(SharingCloud)
    sharing._hass = SimpleNamespace(async_add_executor_job=run_job)
    manager = SimpleNamespace(update_device_cache=dead_update_device_cache)

    async def fake_sleep(delay):
        pass

    monkeypatch.setattr(sharing_cloud_module.asyncio, "sleep", fake_sleep)

    result = await sharing._update_device_cache_with_retry(manager)

    assert result is not None and "token is expired" in result
    assert len(calls) == 3


def _sharing_for_connect_test(monkeypatch, sessions, managers):
    """Build a SharingCloud restored-from-entry-blob with faked IO."""

    async def run_job(fn, *args):
        return fn(*args)

    async def fake_sleep(delay):
        pass

    monkeypatch.setattr(sharing_cloud_module.asyncio, "sleep", fake_sleep)

    blob = {
        sharing_cloud_module.CONF_USER_CODE: "uc",
        sharing_cloud_module.CONF_TERMINAL_ID: "tid",
        sharing_cloud_module.CONF_ENDPOINT: "https://x",
        sharing_cloud_module.CONF_TOKEN_INFO: {"access_token": "old"},
    }
    sharing = object.__new__(SharingCloud)
    sharing._hass = SimpleNamespace(
        async_add_executor_job=run_job,
        config_entries=SimpleNamespace(async_entries=lambda domain: []),
    )
    sharing._store = SimpleNamespace(async_load=AsyncMock(return_value=sessions))
    sharing._auth = blob
    sharing.user_code = "uc"
    sharing.device_list = {}
    sharing._get_manager = AsyncMock(side_effect=list(managers))
    return sharing, blob


@pytest.mark.asyncio
async def test_sharing_cloud_connect_network_failure_never_kills_session(monkeypatch):
    """Boot-time DNS/network trouble must not be treated as session death."""

    def net_err_update():
        raise TimeoutError("connection to endpoint timed out")

    manager = SimpleNamespace(update_device_cache=net_err_update)
    sharing, _blob = _sharing_for_connect_test(monkeypatch, {}, [manager])

    status, res = await sharing.async_connect()

    assert status == "cloud_unavailable"
    assert "timed out" in res
    # A re-auth flow keys off these markers; a plain network error carries none.
    assert not sharing_cloud_module.is_auth_error(res)


@pytest.mark.asyncio
async def test_sharing_cloud_connect_repairs_rotated_tokens_from_store(monkeypatch):
    """A single-use refresh-token rotation race heals from the newest store."""

    def sign_invalid_update():
        raise RuntimeError("sign invalid rejected")

    stale_manager = SimpleNamespace(update_device_cache=sign_invalid_update)
    healed_device = SimpleNamespace(
        id="dev",
        name="Dev",
        local_key="k",
        category="cz",
        product_id="p",
        product_name="Prod",
        model="M1",
        uuid="u1",
        online=True,
        sub=False,
    )
    healed_manager = SimpleNamespace(
        device_map={"dev": healed_device}, update_device_cache=lambda: None
    )

    fresh_token_info = {"access_token": "rotated-fresh", "refresh_token": "r2"}
    fresh_blob = {
        sharing_cloud_module.CONF_USER_CODE: "uc",
        sharing_cloud_module.CONF_TOKEN_INFO: fresh_token_info,
    }
    sharing, blob = _sharing_for_connect_test(
        monkeypatch, {"uc": fresh_blob}, [stale_manager, healed_manager]
    )

    status, res = await sharing.async_connect()

    assert (status, res) == (True, "ok")
    assert sharing._auth[sharing_cloud_module.CONF_TOKEN_INFO] is fresh_token_info
    assert sharing.device_list["dev"]["local_key"] == "k"
    assert sharing._get_manager.await_count == 2


@pytest.mark.asyncio
async def test_sharing_cloud_connect_reports_dead_session_without_repair(monkeypatch):
    """No newer stored tokens -> genuine rejection surfaces for re-auth."""

    def sign_invalid_update():
        raise RuntimeError("sign invalid rejected")

    manager = SimpleNamespace(update_device_cache=sign_invalid_update)
    # Store holds the SAME token info as the entry blob: nothing fresher.
    same_blob = {
        sharing_cloud_module.CONF_USER_CODE: "uc",
        sharing_cloud_module.CONF_TOKEN_INFO: {"access_token": "old"},
    }
    sharing, _blob = _sharing_for_connect_test(
        monkeypatch, {"uc": same_blob}, [manager]
    )

    status, res = await sharing.async_connect()

    assert status == "device_list_failed"
    assert sharing_cloud_module.is_auth_error(res)


def test_is_auth_error_classification():
    assert sharing_cloud_module.is_auth_error(RuntimeError("Sign Invalid resp"))
    assert sharing_cloud_module.is_auth_error("code 1010: token is expired")
    assert not sharing_cloud_module.is_auth_error(TimeoutError("connect timeout"))
    assert not sharing_cloud_module.is_auth_error(None)


def test_missing_cloud_specs_skips_disabled_and_cached(monkeypatch):
    """Startup cloud sync only runs while devices still lack cached specs."""
    import custom_components.localtuya as lt

    entry = SimpleNamespace(
        data={
            "devices": {
                "d1": {},  # no cached cloud data -> cloud needed
                "d2": {DEVICE_CLOUD_DATA: {"local_key": "k"}},  # cached
                "d3": {},  # disabled in HA -> never counted
            }
        }
    )
    monkeypatch.setattr(
        lt, "check_if_device_disabled", lambda hass, entry, dev_id: dev_id == "d3"
    )

    assert lt._missing_cloud_specs(None, entry) == ["d1"]


@pytest.mark.asyncio
async def test_tuya_device_refreshes_after_ble_reconnect(monkeypatch):
    loop = asyncio.get_event_loop()
    monkeypatch.setattr(asyncio, "create_task", loop.create_task)
    device = object.__new__(TuyaDevice)
    device.is_closing = False
    device._task_connect = None
    device._task_ble_refresh = None
    device._task_shutdown_entities = None
    device._node_id = None
    device._interface = SimpleNamespace(
        is_connected=True,
        status=AsyncMock(return_value={1: True}),
    )
    device.status_updated = Mock()
    device.warning = Mock()

    device._handle_ble_connected()
    refresh_task = device._task_ble_refresh
    assert refresh_task is not None
    await refresh_task

    device._interface.status.assert_awaited_once_with(cid=None)
    device.status_updated.assert_called_once_with({1: True})

    device._handle_ble_connected()
    second_refresh_task = device._task_ble_refresh
    assert second_refresh_task is not None
    await second_refresh_task

    assert device._interface.status.await_count == 2
    assert device.status_updated.call_count == 2
    device.status_updated.assert_called_with({1: True})


def _bare_tuya_device(transport, functions=None):
    """Build a TuyaDevice skeleton wired to a BLE device with the given specs."""
    tuya_device = object.__new__(TuyaDevice)
    tuya_device._device_config = SimpleNamespace(transport=transport)
    if transport == TRANSPORT_BLE:
        ble = TuyaBLEDevice(None, SimpleNamespace(address="AA:BB:CC:DD:EE:FF"))
        ble.append_functions(functions or [], [])
        tuya_device._interface = SimpleNamespace(ble_device=ble)
    else:
        tuya_device._interface = None
    return tuya_device


def test_white_mode_supported_derived_from_work_mode_values():
    assert (
        _bare_tuya_device(
            TRANSPORT_BLE,
            [
                {
                    "code": "work_mode",
                    "dp_id": 2,
                    "type": DPType.ENUM,
                    "values": {"0": "color", "1": "music", "2": "scene"},
                }
            ],
        ).white_mode_supported
        is False
    )

    assert (
        _bare_tuya_device(
            TRANSPORT_BLE,
            [
                {
                    "code": "work_mode",
                    "dp_id": 2,
                    "type": DPType.ENUM,
                    "values": {
                        "0": "color",
                        "1": "music",
                        "2": "scene",
                        "3": "white",
                    },
                }
            ],
        ).white_mode_supported
        is True
    )

    assert (
        _bare_tuya_device(
            TRANSPORT_BLE,
            [
                {
                    "code": "work_mode",
                    "dp_id": 2,
                    "type": DPType.ENUM,
                    "values": {},
                }
            ],
        ).white_mode_supported
        is False
    )
    assert _bare_tuya_device(TRANSPORT_BLE).white_mode_supported is True
    assert _bare_tuya_device(TRANSPORT_ETHERNET).white_mode_supported is True


def test_color_data_spec_derived_from_ble_function():
    device = _bare_tuya_device(
        TRANSPORT_BLE,
        [
            {
                "code": "colour_data",
                "dp_id": 5,
                "type": DPType.STRING,
                "values": {
                    "h": {"min": 0, "max": 360, "scale": 0, "step": 1},
                    "s": {"min": 0, "max": 1000, "scale": 0, "step": 1},
                    "v": {"min": 0, "max": 1000, "scale": 0, "step": 1},
                },
            }
        ],
    )

    spec = device.color_data_spec
    assert spec is not None
    assert spec["h"]["max"] == 360
    assert spec["s"]["max"] == 1000


def test_color_data_spec_from_ethernet_cloud_dps_data():
    tuya_device = object.__new__(TuyaDevice)
    tuya_device._device_config = SimpleNamespace(transport=TRANSPORT_ETHERNET)
    tuya_device._interface = None
    tuya_device.id = "device_id"
    tuya_device._hass_entry = SimpleNamespace(
        cloud_data=SimpleNamespace(
            device_list={
                "device_id": {
                    "dps_data": {
                        "5": {
                            "code": "colour_data",
                            "values": (
                                '{"h": {"min": 0, "max": 360},'
                                ' "s": {"min": 0, "max": 1000},'
                                ' "v": {"min": 0, "max": 1000}}'
                            ),
                        }
                    }
                }
            }
        )
    )

    spec = tuya_device.color_data_spec
    assert spec is not None
    assert spec["h"]["max"] == 360
    assert spec["v"]["max"] == 1000


def test_color_type_data_remaps_hue_from_cloud_spec():
    from custom_components.localtuya.light import ColorTypeData

    color_type = ColorTypeData.from_config(
        {"h": {"min": 0, "max": 100}, "s": {"min": 0, "max": 1000}}
    )
    assert color_type is not None

    # HA hue 240 (0-360) maps into the device's 0-100 hue range.
    assert color_type.remap_h_from(240) == 67
    # Hue 90 maps cleanly in both directions (round-trip stable).
    assert color_type.remap_h_from(90) == 25
    assert color_type.remap_h_to(25) == 90
    # Full saturation maps to the device's 0-1000 range and back.
    assert color_type.remap_s_from(100) == 1000
    assert color_type.remap_s_to(1000) == 100

    # Default ranges (user's strip) are identity on the v2 wire format.
    default_type = ColorTypeData.from_config(
        {"h": {"min": 0, "max": 360}, "s": {"min": 0, "max": 1000}}
    )
    assert default_type.remap_h_from(240) == 240
    assert default_type.remap_s_from(50) == 500


# ---------------------------------------------------------------------------
# BLE offline reconnect: persist credentials/specs and read them back first
# ---------------------------------------------------------------------------


def _persisted_cloud_data() -> dict:
    """A complete DEVICE_CLOUD_DATA snapshot (post-setup, post-writeback)."""
    return {
        "id": "dev123",
        "name": "Bedroom strip",
        "uuid": "uuid-abc",
        "local_key": "0123456789abcdef",
        "category": "dd",
        "product_id": "prod-1",
        "product_name": "Strip",
        "model": "model-1",
        "ble_specs": {
            "functions": [
                {"dp_id": 20, "code": "switch_led", "type": "Boolean", "values": None}
            ],
            "status_range": [],
        },
    }


def _make_manager(persisted=None):
    from custom_components.localtuya.core.ble_manager import TuyaBLEDeviceManager

    cloud = SimpleNamespace(device_list={})
    return TuyaBLEDeviceManager(
        SimpleNamespace(), cloud, "dev123", "0123456789abcdef", persisted
    )


async def test_ble_credentials_read_persisted_without_cloud():
    """A complete persisted snapshot avoids any cloud call."""
    manager = _make_manager(_persisted_cloud_data())
    manager._resolve_credentials_from_cloud = AsyncMock()

    creds = await manager._resolve_credentials("AA:BB:CC:DD:EE:FF", False)

    manager._resolve_credentials_from_cloud.assert_not_awaited()
    assert creds["uuid"] == "uuid-abc"
    assert creds["category"] == "dd"
    assert creds["functions"][0]["code"] == "switch_led"


async def test_ble_credentials_fall_back_to_cloud_when_snapshot_incomplete():
    """An incomplete snapshot (no ble_specs) falls back to the cloud."""
    manager = _make_manager({"uuid": "uuid-abc", "category": "dd", "product_id": "p"})
    manager._resolve_credentials_from_cloud = AsyncMock(
        return_value={"uuid": "uuid-abc"}
    )

    creds = await manager._resolve_credentials("AA:BB:CC:DD:EE:FF", False)

    manager._resolve_credentials_from_cloud.assert_awaited_once()
    assert creds["uuid"] == "uuid-abc"


async def test_ble_credentials_force_update_skips_persisted():
    """force_update bypasses the persisted snapshot and hits the cloud."""
    manager = _make_manager(_persisted_cloud_data())
    manager._resolve_credentials_from_cloud = AsyncMock(
        return_value={"uuid": "fresh-uuid"}
    )

    creds = await manager._resolve_credentials("AA:BB:CC:DD:EE:FF", True)

    manager._resolve_credentials_from_cloud.assert_awaited_once()
    assert creds["uuid"] == "fresh-uuid"


def test_ble_credentials_from_persisted_missing_identity_returns_none():
    """Missing identity fields mean the snapshot cannot be used offline."""
    manager = _make_manager({"ble_specs": {"functions": [], "status_range": []}})
    assert manager._credentials_from_persisted() is None


def test_persisted_dps_values_parses_dps_strings():
    """Detected DP values are recovered from the persisted dps_strings list.

    These drive value-dependent description gating (``contains_any``) at setup
    time, before the device reconnects and populates live status.
    """
    tuya_device = object.__new__(TuyaDevice)
    tuya_device._device_config = SimpleNamespace(
        dps_strings=[
            "38 ( code: relay_status , value: on )",
            "9 ( value: 0 )",
            "20 ( value: -1 )",
            "1 (value: ?)",
            "99 ( code: cloud_only , value: , cloud pull )",
        ]
    )

    assert tuya_device.persisted_dps_values == {
        "38": "on",
        "9": "0",
    }


def test_cloud_dpspec_view_handles_missing_dps_data():
    """An offline BLE device (no dps_data) must not crash spec resolution.

    Regression for the platform-setup crash seen when a configured BLE device
    is not found at startup: ``_cloud_device_data`` used to write
    ``dps_data = None`` into the live cloud entry, which then crashed
    ``_cloud_dpspec_view`` with "'NoneType' object has no attribute 'items'".
    """
    tuya_device = object.__new__(TuyaDevice)
    tuya_device.id = "device_id"
    tuya_device._interface = None
    tuya_device._device_config = SimpleNamespace(
        transport=TRANSPORT_ETHERNET, as_dict=lambda: {}
    )
    tuya_device._hass_entry = SimpleNamespace(
        cloud_data=SimpleNamespace(
            device_list={"device_id": {"id": "device_id", "category": "dd"}}
        )
    )

    assert tuya_device._cloud_dpspec_view() == {}


def test_cloud_device_data_handles_none_persisted_snapshot():
    """A None DEVICE_CLOUD_DATA snapshot must resolve to an empty dict."""
    tuya_device = object.__new__(TuyaDevice)
    tuya_device.id = "device_id"
    tuya_device._interface = None
    tuya_device._device_config = SimpleNamespace(
        transport=TRANSPORT_ETHERNET,
        as_dict=lambda: {DEVICE_CLOUD_DATA: None},
    )
    tuya_device._hass_entry = SimpleNamespace(
        cloud_data=SimpleNamespace(device_list={})
    )

    assert tuya_device._cloud_device_data() == {}


def test_dispatcher_discards_buffer_on_corrupt_header():
    """A header claiming >2000 bytes must discard the buffer, not grow it."""
    dispatcher = MessageDispatcher("devid", Mock(), 3.1, "0123456789abcdef")
    dispatcher.set_logger(logging.getLogger("test"), "devid")

    corrupt = (
        Affix.prefix_55aa.bin
        + struct.pack(">III", 1, 8, 3000)  # seqno, cmd, length > 2000
        + b"\x00" * 8
        + Affix.suffix_55aa.bin
    )

    # Before the fix this raised DecodeError and left the buffer intact.
    dispatcher.add_data(corrupt)

    assert dispatcher.buffer == b""


@pytest.mark.asyncio
async def test_ble_reconnect_task_is_deduplicated():
    """Repeated disconnects must not pile up reconnect tasks."""
    device = TuyaBLEDevice(None, SimpleNamespace(address="AA:BB:CC:DD:EE:FF"))
    device._is_paired = True
    device._expected_disconnect = False

    async def _fake_reconnect():
        return None

    device._reconnect = _fake_reconnect
    client = SimpleNamespace(is_connected=False)

    device._disconnected(client)
    first = device._reconnect_task
    assert first is not None

    device._is_paired = True
    device._disconnected(client)

    assert device._reconnect_task is first
    await first


@pytest.mark.asyncio
async def test_ble_stop_cancels_pending_reconnect():
    """stop() cancels a pending reconnect task."""
    device = TuyaBLEDevice(None, SimpleNamespace(address="AA:BB:CC:DD:EE:FF"))
    device._execute_disconnect = AsyncMock()

    task = asyncio.create_task(asyncio.sleep(10))
    device._reconnect_task = task

    await device.stop()

    assert device._reconnect_task is None
    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.asyncio
async def test_dispatcher_timeout_aborts_only_timed_out_listener():
    """A timed-out command must not cancel unrelated in-flight listeners.

    Regression for the abort-cascade: the old ``wait_for`` called
    ``abort()`` on any timeout, cancelling every other listener (status
    refresh, heartbeats) and triggering spurious reconnects.
    """
    dispatcher = MessageDispatcher("devid", Mock(), 3.1, "0123456789abcdef")
    dispatcher.set_logger(logging.getLogger("test"), "devid")

    survivor = asyncio.Future()
    dispatcher.listeners[42] = survivor

    with pytest.raises(TimeoutError):
        await dispatcher.wait_for(7, 1, timeout=0.01)

    assert 42 in dispatcher.listeners
    assert not survivor.cancelled()
    assert 7 not in dispatcher.listeners


@pytest.mark.asyncio
async def test_connect_subdevices_task_is_deduplicated():
    """A pending _connect_subdevices task must not be re-spawned.

    Mirrors the dedup guard in ``_make_connection``: only one task may run
    at a time, and the handle is cleared when it completes.
    """
    device = object.__new__(TuyaDevice)
    device._task_connect_subdevices = None
    device.sub_devices = {"s1": SimpleNamespace(async_connect=AsyncMock())}
    device._interface = SimpleNamespace(is_connected=True)
    device.is_closing = False

    if (
        device._task_connect_subdevices is None
        or device._task_connect_subdevices.done()
    ):
        device._task_connect_subdevices = asyncio.create_task(
            device._connect_subdevices()
        )
    first = device._task_connect_subdevices
    assert first is not None

    if (
        device._task_connect_subdevices is None
        or device._task_connect_subdevices.done()
    ):
        device._task_connect_subdevices = asyncio.create_task(
            device._connect_subdevices()
        )
    assert device._task_connect_subdevices is first

    await first
    assert device._task_connect_subdevices is None


def test_ble_notification_rejects_oversized_input_length():
    """A notification claiming an unreasonable length must not grow the buffer.

    Regression for the unbounded ``_input_buffer`` growth: the expected
    length varint could claim up to 2^35 bytes and the buffer would grow
    toward it until the guard tripped.
    """
    device = TuyaBLEDevice(None, SimpleNamespace(address="AA:BB:CC:DD:EE:FF"))
    device._input_expected_packet_num = 0

    data = (
        TuyaBLEDevice._pack_int(0)  # packet_num = 0
        + TuyaBLEDevice._pack_int(0x1000000)  # claimed length > MAX_INPUT_LENGTH
        + b"\x00"  # skipped byte after the length varint
        + b"\x00" * 4  # payload chunk
    )

    device._notification_handler(None, bytearray(data))

    assert device._input_buffer is None  # _clean_input() ran
    assert device._input_expected_length == 0
    assert device._input_expected_packet_num == 0


def test_ble_notification_discards_bad_length_varint():
    """A 5-byte length varint (>= 2^28) must be cleaned up, not raise.

    ``_unpack_int`` rejects 5-byte varints with ``TuyaBLEDataFormatError``
    before the MAX_INPUT_LENGTH guard runs; the handler now converts that
    into the same graceful discard path instead of raising out of the
    bleak notification callback.
    """
    device = TuyaBLEDevice(None, SimpleNamespace(address="AA:BB:CC:DD:EE:FF"))
    device._input_expected_packet_num = 0

    data = (
        TuyaBLEDevice._pack_int(0)  # packet_num = 0
        + TuyaBLEDevice._pack_int(0x10000000)  # 5-byte varint -> DataFormatError
        + b"\x00"
        + b"\x00" * 4
    )

    device._notification_handler(None, bytearray(data))

    assert device._input_buffer is None
    assert device._input_expected_length == 0
    assert device._input_expected_packet_num == 0


@pytest.mark.asyncio
async def test_abort_connect_retains_ble_transport_on_transient_failure():
    """A transient BLE connect failure must keep the transport (no rebuild).

    Tearing the BLE transport down on every failed attempt forced
    ``async_prepare_ble``'s pre-built stack (manager, device, transport,
    callbacks) to be rebuilt from scratch on each reconnect.
    """
    device = object.__new__(TuyaDevice)
    device._node_id = None
    device._fake_gateway = False
    device._device_config = SimpleNamespace(transport=TRANSPORT_BLE)
    device.is_closing = False
    device._unsub_fingerbot = None
    interface = SimpleNamespace(close=AsyncMock())
    device._interface = interface

    await device.abort_connect()

    assert device._interface is interface
    interface.close.assert_not_awaited()


@pytest.mark.asyncio
async def test_abort_connect_closes_ble_transport_on_close():
    """close() (is_closing) must still tear the BLE transport down."""
    device = object.__new__(TuyaDevice)
    device._node_id = None
    device._fake_gateway = False
    device._device_config = SimpleNamespace(transport=TRANSPORT_BLE)
    device.is_closing = True
    device._unsub_fingerbot = None
    interface = SimpleNamespace(close=AsyncMock())
    device._interface = interface

    await device.abort_connect()

    assert device._interface is None
    interface.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_abort_connect_closes_ethernet_transport_on_failure():
    """Ethernet transports still close on abort (rebuild is the norm there)."""
    device = object.__new__(TuyaDevice)
    device._node_id = None
    device._fake_gateway = False
    device._device_config = SimpleNamespace(transport=TRANSPORT_ETHERNET)
    device.is_closing = False
    device._unsub_fingerbot = None
    interface = SimpleNamespace(close=AsyncMock())
    device._interface = interface

    await device.abort_connect()

    assert device._interface is None
    interface.close.assert_awaited_once()
