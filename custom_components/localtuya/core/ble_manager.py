"""Concrete Tuya BLE device-credentials manager built on localtuya's cloud API.

This implements the abstract ``AbstaractTuyaBLEDeviceManager`` contract (see
``core/tuya_ble_lib/manager.py``) using localtuya's existing ``TuyaCloudApi``
(``core/cloud_api.py``) instead of the reference project's ``tuya_iot`` /
``TuyaOpenAPI`` stack.

Credential resolution (Q6 - Option A): pass 1 does NOT use the factory-info MAC
map API. The user manually enters ``ble_address`` in the config, and the config
already holds the cloud ``device_id`` + ``local_key``. So credentials are
resolved via the configured ``device_id`` against the cloud device list, rather
than scanning factory-info per MAC address.
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
    (and ``local_key``) are used to resolve the BLE credentials, since pass 1
    does not implement the factory-info MAC map (Q6 Option A).
    """

    def __init__(
        self,
        hass: HomeAssistant,
        cloud_api: TuyaCloudApi,
        device_id: str,
        local_key: str | None = None,
    ) -> None:
        """Initialize the manager.

        ``cloud_api`` is the already-configured ``TuyaCloudApi`` instance
        (``HassLocalTuyaData.cloud_data``). ``device_id`` / ``local_key`` come
        from the device config entry.
        """
        self._hass = hass
        self._cloud_api = cloud_api
        self._device_id = device_id
        self._local_key = local_key
        self._data: dict[str, Any] = {}

    async def get_device_credentials(
        self,
        address: str,
        force_update: bool = False,
        save_data: bool = False,
    ) -> TuyaBLEDeviceCredentials | None:
        """Get credentials of the Tuya BLE device.

        The ``address`` argument is ignored for resolution (pass 1 resolves via
        the configured ``device_id``); it is kept to satisfy the abstract
        interface signature.
        """
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

        # Pull functions/status_range from the device specifications.
        functions: list = []
        status_range: list = []
        spec = await self._cloud_api.async_get_device_specifications(self._device_id)
        if isinstance(spec, tuple) and len(spec) == 2 and spec[1] == "ok":
            functions = spec[0].get("functions", []) or []
            status_range = spec[0].get("status", []) or []

        credentials = {
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

        if result is None:
            _LOGGER.debug(
                "BLE device %s: missing required credential fields for %s",
                address,
                self._device_id,
            )
        elif save_data:
            self._data = credentials

        return result

    @property
    def data(self) -> dict[str, Any]:
        """Return the last resolved credentials (if ``save_data`` was used)."""
        return self._data