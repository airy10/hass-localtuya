"""Smart Life QR-code cloud auth (tuya-device-sharing-sdk) for LocalTuya.

Drop-in replacement for the legacy IoT-Platform login (``TuyaCloudApi``):
the user scans a QR with the Smart Life app one single time; the resulting
session is persisted in a HA Store and reused on subsequent flows/runs.

The ``SharingCloud`` exposes the same surface the rest of the integration
consumes from ``TuyaCloudApi`` (``device_list``, ``async_get_devices_list``,
``async_get_device_functions``, ...) so it can be swapped in transparently.

Ported from constantini21/tuya-ble-selfhost commit
109ef439d0534de3ab5a27a816fe5ec952d73a05 ("feat: login por QR do Smart Life
(tuya-device-sharing-sdk)", 2026-08-07, MIT) - ``custom_components/tuya_ble/
sharing.py`` - and adapted to the localtuya hub model (cloud_session per config
entry instead of per-device credentials).
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from Crypto.Cipher import AES
from tuya_sharing import LoginControl, Manager

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from ..const import (
    CONF_SHARING_DATA,
    CONF_USER_CODE,
    DOMAIN,
    STORAGE_KEY,
    STORAGE_VERSION,
)
from .tuya_ble_lib import SERVICE_UUID
from .tuya_ble_lib.const import MANUFACTURER_DATA_ID

_LOGGER = logging.getLogger(__name__)

# Same public client id/schema used by the official HA Tuya integration.
TUYA_CLIENT_ID = "HA_3y9q4ak7g4ephrvke"
TUYA_SCHEMA = "haauthorize"

CONF_TERMINAL_ID = "terminal_id"
CONF_ENDPOINT = "endpoint"
CONF_TOKEN_INFO = "token_info"
CONF_ACCESS_TOKEN = "access_token"
CONF_REFRESH_TOKEN = "refresh_token"


def decode_uuid_from_advertisement(service_info: Any) -> str | None:
    """Extract the device uuid from the BLE advertisement.

    Mirrors the pairing logic in ``core/tuya_ble_lib/tuya_ble.py``: the AES
    key is ``md5(product_id)`` (from ``service_data[1:]``) and the encrypted
    uuid lives in ``manufacturer_data[6:]``.
    """
    try:
        service_data = (service_info.service_data or {}).get(SERVICE_UUID)
        manufacturer_data = (service_info.manufacturer_data or {}).get(
            MANUFACTURER_DATA_ID
        )
        if (
            not service_data
            or len(service_data) < 2
            or service_data[0] != 0
            or not manufacturer_data
            or len(manufacturer_data) <= 6
        ):
            return None
        raw_product_id = bytes(service_data[1:])
        key = hashlib.md5(raw_product_id).digest()
        cipher = AES.new(key, AES.MODE_CBC, key)
        raw_uuid = cipher.decrypt(bytes(manufacturer_data[6:]))
        return raw_uuid.decode("utf-8")
    except Exception:
        _LOGGER.debug("BLE advertisement without decodable uuid", exc_info=True)
        return None


class _StoreTokenListener:
    """Persist renewed tokens back into the Store."""

    def __init__(self, sharing: "SharingCloud") -> None:
        self._sharing = sharing

    def update_token(self, token_info: dict[str, Any]) -> None:
        self._sharing.schedule_token_update(token_info)


class SharingCloud:
    """Cloud session via the sharing SDK, with the token persisted."""

    def __init__(
        self, hass: HomeAssistant, auth_blob: dict[str, Any] | None = None
    ) -> None:
        self._hass = hass
        self._store: Store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._auth: dict[str, Any] | None = auth_blob
        self._qr_code: str | None = None
        self.user_code: str | None = None
        self.device_list: dict[str, dict[str, Any]] = {}
        self._manager = None
        self._login_control = None

    @property
    def auth_blob(self) -> dict[str, Any] | None:
        """The persisted sharing session (user_code + token_info, ...)."""
        return self._auth

    @property
    def qr_code(self) -> str | None:
        """The last generated QR token from Tuya."""
        return self._qr_code

    @property
    def uid(self) -> str | None:
        """The Smart Life user id of the authorized sharing session."""
        if not self._auth:
            return None
        return self._auth.get(CONF_TOKEN_INFO, {}).get("uid")

    async def _get_login_control(self):
        if self._login_control is None:
            self._login_control = LoginControl()
        return self._login_control

    async def _get_manager(self):
        if self._manager is None and self._auth:
            self._manager = Manager(
                TUYA_CLIENT_ID,
                self._auth[CONF_USER_CODE],
                self._auth[CONF_TERMINAL_ID],
                self._auth[CONF_ENDPOINT],
                self._auth[CONF_TOKEN_INFO],
                _StoreTokenListener(self),
            )
        return self._manager

    async def async_restore(self) -> bool:
        """Restore a persisted sharing session."""
        if self._auth is not None:
            return bool(self._auth.get(CONF_TOKEN_INFO))
        data = await self._store.async_load()
        if not data or not data.get(CONF_TOKEN_INFO):
            return False
        self._auth = data
        self.user_code = data.get(CONF_USER_CODE)
        return True

    async def async_get_qr_code(self, user_code: str) -> str | None:
        """Request a QR code from Tuya for the given Smart Life user code."""
        login = await self._get_login_control()
        response = await self._hass.async_add_executor_job(
            login.qr_code, TUYA_CLIENT_ID, TUYA_SCHEMA, user_code
        )
        if response.get("success", False):
            self.user_code = user_code
            self._qr_code = response["result"]["qrcode"]
            return self._qr_code
        _LOGGER.warning("Failed to generate QR code: %s", response)
        return None

    async def async_login(self) -> bool:
        """Check whether the QR was authorized and persist the session."""
        if not self._qr_code or not self.user_code:
            return False
        login = await self._get_login_control()
        success, info = await self._hass.async_add_executor_job(
            login.login_result,
            self._qr_code,
            TUYA_CLIENT_ID,
            self.user_code,
        )
        if not success:
            _LOGGER.warning("QR login failed: %s", info)
            return False
        self._auth = {
            CONF_USER_CODE: self.user_code,
            CONF_TERMINAL_ID: info[CONF_TERMINAL_ID],
            CONF_ENDPOINT: info[CONF_ENDPOINT],
            "username": info.get("username", "Smart Life"),
            CONF_TOKEN_INFO: {
                "t": info["t"],
                "uid": info["uid"],
                "expire_time": info["expire_time"],
                CONF_ACCESS_TOKEN: info[CONF_ACCESS_TOKEN],
                CONF_REFRESH_TOKEN: info[CONF_REFRESH_TOKEN],
            },
        }
        await self._store.async_save(self._auth)
        return True

    def schedule_token_update(self, token_info: dict[str, Any]) -> None:
        """Queue persistence of refreshed tokens back to the Store."""
        if not self._auth:
            return
        self._auth[CONF_TOKEN_INFO] = token_info

        async def _save() -> None:
            await self._store.async_save(self._auth)
            await self._update_entry_tokens(token_info)

        self._hass.add_job(_save)

    async def _update_entry_tokens(self, token_info: dict[str, Any]) -> None:
        """Refresh CONF_SHARING_DATA in every entry using this session."""
        user_code = self._auth.get(CONF_USER_CODE)
        if not user_code:
            return
        for entry in self._hass.config_entries.async_entries(DOMAIN):
            sharing = entry.data.get(CONF_SHARING_DATA)
            if not sharing or sharing.get(CONF_USER_CODE) != user_code:
                continue
            new_data = {**entry.data, CONF_SHARING_DATA: {**sharing, CONF_TOKEN_INFO: token_info}}
            self._hass.config_entries.async_update_entry(entry, data=new_data)

    async def async_connect(self):
        """Restore the session and load the device list."""
        if not await self.async_restore():
            _LOGGER.warning("No persisted sharing session to restore.")
            return "authentication_failed", "no_sharing_session"
        if (res := await self.async_get_devices_list()) != "ok":
            return "device_list_failed", res
        _LOGGER.info("Sharing cloud connected (%d devices)", len(self.device_list))
        return True, res

    async def async_get_devices_list(self, force_update: bool = False) -> str | None:
        """Populate ``device_list`` from the sharing account homes."""
        manager = await self._get_manager()
        if manager is None:
            return _LOGGER.debug("No sharing session to list devices for")
        try:
            await self._hass.async_add_executor_job(manager.update_device_cache)
        except Exception as err:
            _LOGGER.warning("Sharing session expired/invalid: %s", err)
            return f"session_error: {err}"

        self.device_list = {}
        for device in manager.device_map.values():
            self.device_list[device.id] = self._device_to_dict(device)
        return "ok"

    @staticmethod
    def _device_to_dict(device) -> dict[str, Any]:
        """Map a sharing ``CustomerDevice`` to the localtuya device shape."""
        return {
            "id": device.id,
            "name": device.name,
            "local_key": device.local_key,
            "category": device.category,
            "product_id": device.product_id,
            "product_name": device.product_name,
            "model": getattr(device, "model", "") or "",
            "uuid": getattr(device, "uuid", ""),
            "online": getattr(device, "online", False),
            "sub": getattr(device, "sub", False),
        }

    def _dp_id_for_code(self, device, dpcode: str) -> int | None:
        """Resolve a dpcode to its dp_id via the cloud function/status mapping."""
        for mapping in (device.function, device.status_range):
            f = mapping.get(dpcode)
            if f is not None and getattr(f, "dp_id", None) is not None:
                return f.dp_id
        # Fallback: local_strategy maps dpId -> status_code.
        if local_strategy := getattr(device, "local_strategy", None):
            for dp_id, meta in local_strategy.items():
                if meta.get("status_code") == dpcode:
                    return dp_id
        return None

    def _device_specs(self, device) -> dict[str, Any]:
        """Return functions/status_range shaped like the specifications API."""
        functions = [
            {
                "dp_id": self._dp_id_for_code(device, code),
                "code": f.code,
                "type": f.type,
                "values": f.values,
            }
            for code, f in (device.function or {}).items()
        ]
        status = [
            {
                "dp_id": self._dp_id_for_code(device, code),
                "code": s.code,
                "type": s.type,
                "values": s.values,
            }
            for code, s in (device.status_range or {}).items()
        ]
        return {"functions": functions, "status": status}

    async def async_get_device_specifications(
        self, device_id: str, force_update: bool = False
    ) -> tuple[dict[str, Any], str]:
        """Return the DP functions/status specs for a device."""
        manager = await self._get_manager()
        device = manager.device_map.get(device_id) if manager else None
        if device is None:
            return {}, f"Error: device {device_id} not in sharing device list"
        return self._device_specs(device), "ok"

    async def async_get_device_factory_infos(self, device_id: str):
        """Legacy-only: sharing session matches devices by uuid, not MAC."""
        return "", "not_available"

    async def async_get_device_functions(self, device_id: str) -> dict[str, dict]:
        """Build the localtuya ``dps_data`` shape (keyed by str dp_id)."""
        manager = await self._get_manager()
        device = manager.device_map.get(device_id) if manager else None
        if device is None:
            return {}
        dps_data: dict[str, dict] = {}
        for code, f in (device.function or {}).items():
            dp_id = self._dp_id_for_code(device, code)
            if dp_id is None:
                continue
            dps_data[str(dp_id)] = {
                "code": f.code,
                "type": f.type,
                "values": f.values,
                "accessMode": "rw",
            }
        for code, s in (device.status_range or {}).items():
            dp_id = self._dp_id_for_code(device, code)
            if dp_id is None:
                continue
            existing = dps_data.get(str(dp_id), {})
            existing.update(
                {
                    "code": s.code,
                    "type": s.type,
                    "values": s.values,
                    "accessMode": "ro",
                }
            )
            dps_data[str(dp_id)] = existing
        if device_id in self.device_list:
            self.device_list[device_id]["dps_data"] = dps_data
        return dps_data

    async def async_get_devices_dps_query(self) -> str:
        """Populate dps_data for every device from functions/status_range."""
        for dev_id in self.device_list:
            dps_data = await self.async_get_device_functions(dev_id)
            if dps_data:
                self.device_list[dev_id]["dps_data"] = dps_data
        return "ok"

    @property
    def token_validate(self) -> bool:
        """Return whether the sharing session is available (SDK refreshes internally)."""
        return self._auth is not None