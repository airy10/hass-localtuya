"""Transport abstraction for localtuya device connections.

This module defines the semantic interface that the coordinator
(``coordinator.py::TuyaDevice``) needs from a device connection, regardless of
the underlying transport (Ethernet/TuyaProtocol or BLE/TuyaBLEDevice).

The interface mirrors the subset of ``pytuya.TuyaProtocol`` that the coordinator
actually calls on ``self._interface``. Concrete adapters wrap the real protocol
objects and delegate to them; for pass 1 the BLE adapter is skeletal.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..pytuya import TuyaProtocol
from ..tuya_ble_lib import TuyaBLEDevice


class Transport(ABC):
    """Semantic interface for a device connection used by the coordinator."""

    #: Last dispatched DPS payload (dict of dp -> value), used to fire HA events.
    dispatched_dps: dict[str, Any]

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Return whether the underlying connection is established."""

    @abstractmethod
    def add_dps_to_request(self, dp_indicies) -> None:
        """Add datapoints to be included in status requests."""

    @abstractmethod
    async def status(self, cid: str | None = None) -> dict:
        """Return the current device status as a dict of dp -> value."""

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
    async def keep_alive(self, is_gateway: bool = False) -> None:
        """Start the heartbeat/keep-alive loop with the device."""

    @abstractmethod
    async def close(self) -> None:
        """Close the connection and abort outstanding listeners."""

    @abstractmethod
    async def detect_available_dps(self, cid: str | None = None) -> dict:
        """Return which datapoints are supported by the device."""

    @abstractmethod
    def enable_debug(self, enable: bool = False, friendly_name: str | None = None) -> None:
        """Enable debug logging for the device."""

    @abstractmethod
    def set_updatedps_list(self, update_list) -> None:
        """Set the DPS to be requested with the update command."""


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
    def dispatched_dps(self) -> dict[str, Any]:
        """Return the last dispatched DPS payload."""
        return self._protocol.dispatched_dps

    def add_dps_to_request(self, dp_indicies) -> None:
        """Delegate to the wrapped protocol."""
        self._protocol.add_dps_to_request(dp_indicies)

    async def status(self, cid: str | None = None) -> dict:
        """Return device status."""
        return await self._protocol.status(cid=cid)

    async def reset(self, dp_id=None, cid: str | None = None) -> Any:
        """Reset the device."""
        return await self._protocol.reset(dp_id, cid=cid)

    async def set_dps(self, dps: dict, cid: str | None = None) -> Any:
        """Set values for a set of datapoints."""
        return await self._protocol.set_dps(dps, cid=cid)

    async def update_dps(self, dps=None, cid: str | None = None) -> bool:
        """Request the device to update dps."""
        return await self._protocol.update_dps(dps=dps, cid=cid)

    async def keep_alive(self, is_gateway: bool = False) -> None:
        """Start the heartbeat loop (sync on the protocol, awaited here)."""
        self._protocol.keep_alive(is_gateway=is_gateway)

    async def close(self) -> None:
        """Close the connection."""
        await self._protocol.close()

    async def detect_available_dps(self, cid: str | None = None) -> dict:
        """Return which datapoints are supported by the device."""
        return await self._protocol.detect_available_dps(cid=cid)

    def enable_debug(self, enable: bool = False, friendly_name: str | None = None) -> None:
        """Enable debug logging."""
        self._protocol.enable_debug(enable, friendly_name)

    def set_updatedps_list(self, update_list) -> None:
        """Set the DPS to be requested with the update command."""
        self._protocol.set_updatedps_list(update_list)


class BluetoothTransport(Transport):
    """Thin adapter around a ``TuyaBLEDevice``.

    Pass 1: the BLE adapter is skeletal. The wrapped device is held for later
    wiring; methods that are not yet implemented raise ``NotImplementedError``.
    """

    def __init__(self, device: TuyaBLEDevice) -> None:
        """Initialize the adapter around a TuyaBLEDevice."""
        self._device = device
        self.dispatched_dps: dict[str, Any] = {}

    @property
    def is_connected(self) -> bool:
        """Return whether the BLE device is connected."""
        raise NotImplementedError("BLE transport is not wired yet")

    def add_dps_to_request(self, dp_indicies) -> None:
        """BLE devices do not use a request list; no-op for now."""
        raise NotImplementedError("BLE transport is not wired yet")

    async def status(self, cid: str | None = None) -> dict:
        """Return the current datapoint values."""
        raise NotImplementedError("BLE transport is not wired yet")

    async def reset(self, dp_id=None, cid: str | None = None) -> Any:
        """Reset the device."""
        raise NotImplementedError("BLE transport is not wired yet")

    async def set_dps(self, dps: dict, cid: str | None = None) -> Any:
        """Set values for a set of datapoints."""
        raise NotImplementedError("BLE transport is not wired yet")

    async def update_dps(self, dps=None, cid: str | None = None) -> bool:
        """Request the device to update dps."""
        raise NotImplementedError("BLE transport is not wired yet")

    async def keep_alive(self, is_gateway: bool = False) -> None:
        """Start the keep-alive loop."""
        raise NotImplementedError("BLE transport is not wired yet")

    async def close(self) -> None:
        """Close the connection."""
        raise NotImplementedError("BLE transport is not wired yet")

    async def detect_available_dps(self, cid: str | None = None) -> dict:
        """Detect available datapoints."""
        raise NotImplementedError("BLE transport is not wired yet")

    def enable_debug(self, enable: bool = False, friendly_name: str | None = None) -> None:
        """Enable debug logging."""
        raise NotImplementedError("BLE transport is not wired yet")

    def set_updatedps_list(self, update_list) -> None:
        """Set the DPS to be requested with the update command."""
        raise NotImplementedError("BLE transport is not wired yet")


def create_transport(transport_type: str, **kwargs: Any) -> Transport:
    """Return the transport matching ``transport_type``.

    Supported types:
      - ``"ethernet"``: wraps a ``pytuya.TuyaProtocol`` (pass ``protocol=``).
      - ``"ble"``: wraps a ``TuyaBLEDevice`` (pass ``device=``).
    """
    if transport_type == "ethernet":
        return EthernetTransport(kwargs["protocol"])
    if transport_type == "ble":
        return BluetoothTransport(kwargs["device"])
    raise ValueError(f"Unknown transport type: {transport_type}")