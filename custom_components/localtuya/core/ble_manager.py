"""Concrete Tuya BLE device-credentials manager built on localtuya's cloud API.

This implements the abstract ``AbstaractTuyaBLEDeviceManager`` contract (see
``core/tuya_ble_lib/manager.py``) using localtuya's existing ``TuyaCloudApi``
(``core/cloud_api.py``) instead of the reference project's ``tuya_iot`` /
``TuyaOpenAPI`` stack.

Credential resolution (Q6 - Option A): the configured cloud ``device_id`` +
``local_key`` resolve the BLE credentials against the cloud device list. When a
BLE ``address`` (MAC) is provided it is verified against the device's
factory-info MAC, falling back to the configured ``device_id`` on mismatch.
Resolved credentials are cached per device so reconnects make no repeated cloud
calls.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant

from .cloud_api import TuyaCloudApi
from .tuya_ble_lib.manager import (
    AbstaractTuyaBLEDeviceManager,
    TuyaBLEDeviceCredentials,
)

_LOGGER = logging.getLogger(__name__)


class TuyaBLEDeviceManager(AbstaractTuyaBLEDeviceManager):
    """Cloud connected manager of the Tuya BLE devices credentials.

    Built on localtuya's ``TuyaCloudApi``. The configured cloud ``device_id``
    (and ``local_key``) resolve the BLE credentials; the runtime BLE MAC
    (``address``) is verified against the factory-info MAC when available.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        cloud_api: TuyaCloudApi,
        device_id: str,
        local_key: str | None = None,
        persisted_cloud_data: dict | None = None,
    ) -> None:
        """Initialize the manager.

        ``cloud_api`` is the already-configured ``TuyaCloudApi`` instance
        (``HassLocalTuyaData.cloud_data``). ``device_id`` / ``local_key`` come
        from the device config entry. ``persisted_cloud_data`` is the
        ``DEVICE_CLOUD_DATA`` snapshot stored at setup time; when it holds the
        resolved credentials/specs it is used instead of the cloud, so BLE
        devices reconnect without cloud reachability.
        """
        self._hass = hass
        self._cloud_api = cloud_api
        self._device_id = device_id
        self._local_key = local_key
        self._persisted: dict[str, Any] = persisted_cloud_data or {}
        self._data: dict[str, Any] = {}
        self._credentials_cache: dict[str, dict[str, Any]] = {}

    async def get_device_credentials(
        self,
        address: str,
        force_update: bool = False,
        save_data: bool = False,
    ) -> TuyaBLEDeviceCredentials | None:
        """Get credentials of the Tuya BLE device.

        Resolved credentials are cached per device, so a second call without
        ``force_update`` is a cache hit (no repeated cloud calls).
        """
        if not force_update and self._device_id in self._credentials_cache:
            credentials = self._credentials_cache[self._device_id]
        else:
            credentials = await self._resolve_credentials(address, force_update)
            if credentials:
                self._credentials_cache[self._device_id] = credentials

        if not credentials:
            return None

        result = self.check_and_create_device_credentials(
            credentials["uuid"],
            credentials["local_key"],
            credentials["device_id"],
            credentials["category"],
            credentials["product_id"],
            credentials["device_name"],
            credentials["product_model"],
            credentials["product_name"],
            credentials["functions"],
            credentials["status_range"],
        )

        # Keep the resolved credentials available for the coordinator to
        # persist back into DEVICE_CLOUD_DATA (offline reconnect support).
        self._data = credentials

        if result is None:
            missing = [
                field
                for field, value in {
                    "uuid": credentials.get("uuid"),
                    "local_key": credentials.get("local_key"),
                    "device_id": credentials.get("device_id"),
                    "category": credentials.get("category"),
                    "product_id": credentials.get("product_id"),
                }.items()
                if not value
            ]
            _LOGGER.debug(
                "BLE device %s: missing credential fields for %s: %s "
                "(available keys: %s)",
                address,
                self._device_id,
                missing,
                sorted(credentials.keys()),
            )

        return result

    async def _resolve_credentials(
        self, address: str, force_update: bool
    ) -> dict[str, Any] | None:
        """Resolve device credentials, preferring the persisted snapshot.

        The persisted ``DEVICE_CLOUD_DATA`` snapshot is used when it already
        holds the identity + specs, so reconnects work without the cloud; the
        cloud is only queried when the snapshot is incomplete or a refresh is
        forced.
        """
        if not force_update and (persisted := self._credentials_from_persisted()):
            return persisted
        return await self._resolve_credentials_from_cloud(address, force_update)

    def _credentials_from_persisted(self) -> dict[str, Any] | None:
        """Build credentials from the persisted DEVICE_CLOUD_DATA snapshot.

        Returns None when the snapshot does not hold the identity fields or
        the ``ble_specs`` (functions/status_range), so the caller falls back
        to the cloud.
        """
        persisted = self._persisted or {}
        if not (
            persisted.get("uuid")
            and persisted.get("category")
            and persisted.get("product_id")
            and "ble_specs" in persisted
        ):
            return None
        ble_specs = persisted.get("ble_specs") or {}
        return {
            "uuid": persisted.get("uuid"),
            "local_key": persisted.get("local_key") or self._local_key,
            "device_id": persisted.get("id") or self._device_id,
            "category": persisted.get("category"),
            "product_id": persisted.get("product_id"),
            "device_name": persisted.get("name"),
            "product_model": persisted.get("model"),
            "product_name": persisted.get("product_name"),
            "functions": ble_specs.get("functions"),
            "status_range": ble_specs.get("status_range"),
        }

    async def _resolve_credentials_from_cloud(
        self, address: str, force_update: bool
    ) -> dict[str, Any] | None:
        """Resolve the device credentials from the cloud."""
        # Ensure the cloud device list is loaded (and refresh if forced).
        if not self._cloud_api.device_list or force_update:
            await self._cloud_api.async_get_devices_list(force_update=force_update)

        dev = self._cloud_api.device_list.get(self._device_id)
        if not dev:
            _LOGGER.debug(
                "BLE device %s: cloud device %s not found in device list",
                address,
                self._device_id,
            )
            return None

        # Resolve the MAC from factory-info when an address is provided.
        if address:
            mac = await self._cloud_api.async_get_device_factory_infos(
                self._device_id
            )
            if isinstance(mac, tuple) and len(mac) == 2 and mac[1] == "ok":
                if mac[0] and mac[0] != address.upper():
                    _LOGGER.debug(
                        "BLE device %s: factory-info MAC %s does not match, "
                        "falling back to configured device_id %s",
                        address,
                        mac[0],
                        self._device_id,
                    )

        # Pull functions/status_range from the device specifications.
        functions: list = []
        status_range: list = []
        spec = await self._cloud_api.async_get_device_specifications(
            self._device_id, force_update=force_update
        )
        if isinstance(spec, tuple) and len(spec) == 2 and spec[1] == "ok":
            functions = spec[0].get("functions", []) or []
            status_range = spec[0].get("status", []) or []

        return {
            "uuid": dev.get("uuid"),
            "local_key": dev.get("local_key") or self._local_key,
            "device_id": dev.get("id") or self._device_id,
            "category": dev.get("category"),
            "product_id": dev.get("product_id"),
            "device_name": dev.get("name"),
            "product_model": dev.get("model"),
            "product_name": dev.get("product_name"),
            "functions": functions,
            "status_range": status_range,
        }

    @property
    def data(self) -> dict[str, Any]:
        """Return the last resolved credentials (for offline persistence)."""
        return self._data