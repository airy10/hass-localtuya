"""Transport abstraction for localtuya device connections.

This module defines the semantic interface that the coordinator
(``coordinator.py::TuyaDevice``) needs from a device connection, regardless of
the underlying transport (Ethernet/TuyaProtocol or BLE/TuyaBLEDevice).

The interface mirrors the subset of ``pytuya.TuyaProtocol`` that the coordinator
actually calls on ``self._interface``. Concrete adapters wrap the real protocol
objects and delegate to them; for pass 1 the BLE adapter is skeletal.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from ...const import DPType
from ..pytuya import TuyaProtocol
from ..tuya_ble_lib import TuyaBLEDevice
from ..tuya_ble_lib.const import TuyaBLEDataPointType

_LOGGER = logging.getLogger(__name__)

StatusListener = Callable[[dict[int, Any]], None]
ConnectedListener = Callable[[], None]
DisconnectListener = Callable[[], None]

# Map localtuya's DPType (cloud spec) to the BLE datapoint wire type.
_DPTYPE_TO_BLE: dict[DPType, TuyaBLEDataPointType] = {
    DPType.BOOLEAN: TuyaBLEDataPointType.DT_BOOL,
    DPType.ENUM: TuyaBLEDataPointType.DT_ENUM,
    DPType.INTEGER: TuyaBLEDataPointType.DT_VALUE,
    DPType.JSON: TuyaBLEDataPointType.DT_RAW,
    DPType.RAW: TuyaBLEDataPointType.DT_RAW,
    DPType.STRING: TuyaBLEDataPointType.DT_STRING,
}


class Transport(ABC):
    """Semantic interface for a device connection used by the coordinator."""

    #: Last dispatched DPS payload (dict of numeric dp_id -> value).
    dispatched_dps: dict[int, Any]

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Return whether the underlying connection is established."""

    @abstractmethod
    def add_dps_to_request(self, dp_indicies) -> None:
        """Add datapoints to be included in status requests."""

    @abstractmethod
    async def status(self, cid: str | None = None) -> dict | None:
        """Return the current device status, or None when it is unavailable."""

    @abstractmethod
    async def reset(self, dpIds=None, cid: str | None = None) -> Any:
        """Send a reset message (protocol 3.3 only)."""

    @abstractmethod
    async def set_dps(self, dps: dict, cid: str | None = None) -> Any:
        """Set values for a set of datapoints."""

    @abstractmethod
    async def update_dps(self, dps=None, cid: str | None = None) -> bool:
        """Request the device to update the given (or detected) dps."""

    @abstractmethod
    def keep_alive(self, is_gateway: bool = False) -> None:
        """Start the heartbeat/keep-alive loop with the device."""

    @abstractmethod
    async def close(self) -> None:
        """Close the connection and abort outstanding listeners."""

    @abstractmethod
    async def detect_available_dps(self, cid: str | None = None) -> dict | None:
        """Return supported datapoints, or None when detection is unavailable."""

    @abstractmethod
    def enable_debug(self, enable: bool = False, friendly_name: str | None = None) -> None:
        """Enable debug logging for the device."""

    @abstractmethod
    def set_updatedps_list(self, update_list) -> None:
        """Set the DPS to be requested with the update command."""

    @property
    def rssi(self) -> int | None:
        """Return the received signal strength indicator, if available."""
        return None


class EthernetTransport(Transport):
    """Thin adapter wrapping a ``pytuya.TuyaProtocol`` connection."""

    def __init__(self, protocol: TuyaProtocol) -> None:
        """Wrap an existing TuyaProtocol instance."""
        self._protocol = protocol

    @property
    def is_connected(self) -> bool:
        """Return whether the underlying protocol is connected."""
        return self._protocol.is_connected

    @property
    def dispatched_dps(self) -> dict[int, Any]:
        """Return the last dispatched DPS payload with numeric DP IDs."""
        return self._numeric_status(self._protocol.dispatched_dps)

    @staticmethod
    def _numeric_status(status: dict | None) -> dict[int, Any] | None:
        """Normalize protocol DP keys while preserving an unavailable status."""
        if status is None:
            return None
        return {
            int(dp_id) if str(dp_id).isdigit() else dp_id: value
            for dp_id, value in status.items()
        }

    def add_dps_to_request(self, dp_indicies) -> None:
        """Delegate to the wrapped protocol."""
        self._protocol.add_dps_to_request(dp_indicies)

    async def status(self, cid: str | None = None) -> dict | None:
        """Return device status, preserving an unavailable protocol response."""
        return self._numeric_status(await self._protocol.status(cid=cid))

    async def reset(self, dp_id=None, cid: str | None = None) -> Any:
        """Reset the device."""
        return await self._protocol.reset(dp_id, cid=cid)

    async def set_dps(self, dps: dict, cid: str | None = None) -> Any:
        """Set values for a set of datapoints."""
        return await self._protocol.set_dps(dps, cid=cid)

    async def update_dps(self, dps=None, cid: str | None = None) -> bool:
        """Request the device to update dps."""
        return await self._protocol.update_dps(dps=dps, cid=cid)

    def keep_alive(self, is_gateway: bool = False) -> None:
        """Start the heartbeat loop on the wrapped protocol."""
        self._protocol.keep_alive(is_gateway=is_gateway)

    async def close(self) -> None:
        """Close the connection."""
        await self._protocol.close()

    async def detect_available_dps(self, cid: str | None = None) -> dict | None:
        """Return supported datapoints, preserving an unavailable response."""
        return self._numeric_status(
            await self._protocol.detect_available_dps(cid=cid)
        )

    def enable_debug(self, enable: bool = False, friendly_name: str | None = None) -> None:
        """Enable debug logging."""
        self._protocol.enable_debug(enable, friendly_name)

    def set_updatedps_list(self, update_list) -> None:
        """Set the DPS to be requested with the update command."""
        self._protocol.set_updatedps_list(update_list)


class BluetoothTransport(Transport):
    """Thin adapter around a ``TuyaBLEDevice``.

    Delegates to the wrapped ``TuyaBLEDevice`` (held as ``self._device``). BLE
    devices have no ``cid``; the argument is accepted for interface parity and
    ignored. Runtime DP keys are ``int dp_id`` (Q1), so the dpcode-keyed
    ``TuyaBLEDevice.status`` is re-keyed to dp_id via the function/status_range
    mapping.
    """

    def __init__(
        self,
        device: TuyaBLEDevice,
        status_listener: StatusListener | None = None,
        connected_listener: ConnectedListener | None = None,
        disconnect_listener: DisconnectListener | None = None,
    ) -> None:
        """Initialize the adapter around a TuyaBLEDevice."""
        self._device = device
        self.dispatched_dps: dict[int, Any] = {}
        self._requested_dps: list | None = None
        self._status_listener = status_listener
        self._connected_listener = connected_listener
        self._disconnect_listener = disconnect_listener
        self._closed = False
        self._unregister_callback = device.register_callback(self._handle_datapoints)
        self._unregister_connected_callback = device.register_connected_callback(
            self._handle_connected
        )
        self._unregister_disconnected_callback = device.register_disconnected_callback(
            self._handle_disconnect
        )

    @property
    def ble_device(self) -> TuyaBLEDevice:
        """Return the wrapped TuyaBLEDevice (for auto-config mapping lookup)."""
        return self._device

    def _handle_datapoints(self, datapoints) -> None:
        """Forward changed datapoints and retain them for event detection."""
        status = {datapoint.id: datapoint.value for datapoint in datapoints}
        if not status:
            return
        self.dispatched_dps = status
        if self._status_listener is not None:
            try:
                self._status_listener(status)
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("BLE status listener failed")

    def _handle_connected(self) -> None:
        """Forward a successful reconnect to the owning coordinator."""
        if not self._closed and self._connected_listener is not None:
            try:
                self._connected_listener()
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("BLE connected listener failed")

    def _handle_disconnect(self) -> None:
        """Forward unexpected disconnects to the owning coordinator."""
        if not self._closed and self._disconnect_listener is not None:
            try:
                self._disconnect_listener()
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("BLE disconnect listener failed")

    def _dp_id_for_code(self, dpcode: str) -> int | None:
        """Resolve a dpcode to its dp_id via the cloud function/status mapping."""
        f = self._device.function.get(dpcode)
        if f is None:
            f = self._device.status_range.get(dpcode)
        return f.dp_id if f else None

    def _status_by_dp_id(self) -> dict[int, Any]:
        """Return the device status keyed by dp_id (Q1 runtime key)."""
        result: dict[str, Any] = {}
        for dpcode, value in self._device.status.items():
            dp_id = self._dp_id_for_code(dpcode)
            if dp_id is not None:
                result[dp_id] = value
        return result

    def _datapoint_type_for_id(self, dp_id: int) -> TuyaBLEDataPointType | None:
        """Map a dp_id to its BLE datapoint type via the cloud mapping."""
        for funcs in (self._device.function, self._device.status_range):
            for f in funcs.values():
                if f.dp_id == dp_id:
                    return _DPTYPE_TO_BLE.get(f.type)
        return None

    @property
    def is_connected(self) -> bool:
        """Return whether the BLE device is connected."""
        return self._device.is_connected

    @property
    def rssi(self) -> int | None:
        """Return the BLE signal strength."""
        return self._device.rssi

    def add_dps_to_request(self, dp_indicies) -> None:
        """Store the requested dps so ``status()`` can filter (BLE has no request list)."""
        self._requested_dps = list(dp_indicies)

    async def status(self, cid: str | None = None) -> dict:
        """Return the current datapoint values keyed by dp_id."""
        await self._device.update()
        self.dispatched_dps = self._status_by_dp_id()
        return self.dispatched_dps

    async def reset(self, dp_id=None, cid: str | None = None) -> Any:
        """Reset is not applicable to BLE; no-op."""
        return None

    async def set_dps(self, dps: dict, cid: str | None = None) -> Any:
        """Set values for a set of datapoints."""
        for dp_id, value in dps.items():
            dp_id = int(dp_id)
            dp = self._device.datapoints.get_or_create(
                dp_id, self._datapoint_type_for_id(dp_id), value
            )
            await dp.set_value(value)

    async def update_dps(self, dps=None, cid: str | None = None) -> bool:
        """Request the device to update dps."""
        await self._device.update()
        self.dispatched_dps = self._status_by_dp_id()
        return True

    def keep_alive(self, is_gateway: bool = False) -> None:
        """BLE manages its own connection lifecycle; no-op heartbeat."""
        _LOGGER.debug("BLE transport keep_alive: no-op (device manages reconnect)")

    async def close(self) -> None:
        """Close the connection and unregister all listeners."""
        if self._closed:
            return
        self._closed = True
        if self._unregister_callback is not None:
            self._unregister_callback()
            self._unregister_callback = None
        if self._unregister_connected_callback is not None:
            self._unregister_connected_callback()
            self._unregister_connected_callback = None
        if self._unregister_disconnected_callback is not None:
            self._unregister_disconnected_callback()
            self._unregister_disconnected_callback = None
        await self._device.stop()

    async def detect_available_dps(self, cid: str | None = None) -> dict:
        """Return the datapoint ids currently known from the device."""
        return self._status_by_dp_id()

    def enable_debug(self, enable: bool = False, friendly_name: str | None = None) -> None:
        """Enable debug logging (BLE lib logs already; no-op)."""
        _LOGGER.debug("BLE enable_debug(%s) for %s", enable, friendly_name)

    def set_updatedps_list(self, update_list) -> None:
        """BLE has no such concept; no-op."""


def create_transport(transport_type: str, **kwargs: Any) -> Transport:
    """Return the transport matching ``transport_type``.

    Supported types:
      - ``"ethernet"``: wraps a ``pytuya.TuyaProtocol`` (pass ``protocol=``).
      - ``"ble"``: wraps a ``TuyaBLEDevice`` (pass ``device=``).
    """
    if transport_type == "ethernet":
        return EthernetTransport(kwargs["protocol"])
    if transport_type == "ble":
        return BluetoothTransport(
            kwargs["device"],
            status_listener=kwargs.get("status_listener"),
            connected_listener=kwargs.get("connected_listener"),
            disconnect_listener=kwargs.get("disconnect_listener"),
        )
    raise ValueError(f"Unknown transport type: {transport_type}")