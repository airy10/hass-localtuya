"""Regression tests for the BLE transport review fixes."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from bleak_retry_connector import BleakError

from custom_components.localtuya.const import DPType, TRANSPORT_BLE, TRANSPORT_ETHERNET
from custom_components.localtuya.coordinator import TuyaDevice
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
                "values": "{\"min\":0}",
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
