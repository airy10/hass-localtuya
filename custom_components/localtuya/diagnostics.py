"""Diagnostics support for LocalTuya."""

from __future__ import annotations

import copy
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_CLIENT_ID, CONF_CLIENT_SECRET, CONF_DEVICES
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry

from . import HassLocalTuyaData
from .const import (
    CONF_LOCAL_KEY,
    CONF_SHARING_DATA,
    CONF_USER_ID,
    DOMAIN,
    CONF_NO_CLOUD,
    DATA_DISCOVERY,
)

CLOUD_DEVICES = "cloud_devices"
DEVICE_CONFIG = "device_config"
DEVICE_CLOUD_INFO = "device_cloud_info"

_LOGGER = logging.getLogger(__name__)

DATA_OBFUSCATE = {
    "ip": 1,
    "uid": 3,
    CONF_LOCAL_KEY: 3,
    "lat": 0,
    "lon": 0,
    "ble_address": 1,
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    data = {}
    data = dict(entry.data)
    hass_localtuya: HassLocalTuyaData = hass.data[DOMAIN][entry.entry_id]
    tuya_api = hass_localtuya.cloud_data
    if data.get(CONF_NO_CLOUD, True) is not True:
        await hass.async_create_task(tuya_api.async_get_devices_dps_query())
    # censoring private information on integration diagnostic data
    for field in [CONF_CLIENT_ID, CONF_CLIENT_SECRET, CONF_USER_ID]:
        if value := data.get(field):
            data[field] = obfuscate(value)
    # The sharing session blob carries OAuth tokens; never leak them.
    data.pop(CONF_SHARING_DATA, None)
    data[CONF_DEVICES] = copy.deepcopy(entry.data[CONF_DEVICES])
    for dev_id, dev in data[CONF_DEVICES].items():
        local_key = dev[CONF_LOCAL_KEY]
        local_key_obfuscated = obfuscate(local_key)
        dev[CONF_LOCAL_KEY] = local_key_obfuscated
    data[CLOUD_DEVICES] = copy.deepcopy(tuya_api.device_list)
    for dev_id, dev in data[CLOUD_DEVICES].items():
        for obf, obf_len in DATA_OBFUSCATE.items():
            if ob := data[CLOUD_DEVICES][dev_id].get(obf):
                data[CLOUD_DEVICES][dev_id][obf] = obfuscate(ob, obf_len, obf_len)
    if discovery := hass.data[DOMAIN].get(DATA_DISCOVERY):
        data["Discovered_Devices"] = discovery.devices
    # Per-device cloud specs for bulk diagnostics
    cloud_specs: dict[str, dict[str, Any]] = {}
    for dev_id, dev in data[CLOUD_DEVICES].items():
        cloud_specs[dev_id] = {
            "category": dev.get("category", ""),
            "product_id": dev.get("product_id", ""),
            "product_name": dev.get("product_name", dev.get("name", "")),
        }
        if "dps_data" in dev:
            cloud_specs[dev_id]["dps"] = copy.deepcopy(dev["dps_data"])
    data["cloud_specs"] = cloud_specs
    return data


async def async_get_device_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry, device: DeviceEntry
) -> dict[str, Any]:
    """Return diagnostics for a device entry."""
    data = {}
    dev_id = list(device.identifiers)[0][1].split("_")[-1]
    data[DEVICE_CONFIG] = entry.data[CONF_DEVICES][dev_id].copy()
    # NOT censoring private information on device diagnostic data
    # local_key = data[DEVICE_CONFIG][CONF_LOCAL_KEY]
    # data[DEVICE_CONFIG][CONF_LOCAL_KEY] = f"{local_key[0:3]}...{local_key[-3:]}"

    hass_localtuya: HassLocalTuyaData = hass.data[DOMAIN][entry.entry_id]
    tuya_api = hass_localtuya.cloud_data
    if dev_id in tuya_api.device_list:
        await tuya_api.async_get_device_functions(dev_id)
        data[DEVICE_CLOUD_INFO] = copy.deepcopy(tuya_api.device_list[dev_id])
        for obf, obf_len in DATA_OBFUSCATE.items():
            if ob := data[DEVICE_CLOUD_INFO].get(obf):
                data[DEVICE_CLOUD_INFO][obf] = obfuscate(ob, obf_len, obf_len)
        # NOT censoring private information on device diagnostic data
        # local_key = data[DEVICE_CLOUD_INFO][CONF_LOCAL_KEY]
        # local_key_obfuscated = "{local_key[0:3]}...{local_key[-3:]}"
        # data[DEVICE_CLOUD_INFO][CONF_LOCAL_KEY] = local_key_obfuscated

    # data["log"] = hass.data[DOMAIN][CONF_DEVICES][dev_id].logger.retrieve_log()
    if discovery := hass.data[DOMAIN].get(DATA_DISCOVERY):
        data["Discovered_Devices"] = discovery.devices.get(dev_id)

    # Build a cloud_spec summary mirroring core tuya diagnostics:
    # category, product info, dpcode→type/values.  Makes "add support for
    # my device" bug reports a single paste away.
    cloud_info = data.get(DEVICE_CLOUD_INFO, {})
    cloud_spec: dict[str, Any] = {
        "category": cloud_info.get("category", ""),
        "product_id": cloud_info.get("product_id", ""),
        "product_name": cloud_info.get("product_name", cloud_info.get("name", "")),
    }
    if "dps_data" in cloud_info:
        cloud_spec["dps"] = copy.deepcopy(cloud_info["dps_data"])
    data["cloud_spec"] = cloud_spec

    # Surface the parsed BLE spec (function/status_range) and live status,
    # mirroring core tuya's customer_device_as_dict (diagnostics include
    # function/status_range/status for the device).
    for device_key, tuya_device in hass_localtuya.devices.items():
        if tuya_device.id != dev_id:
            continue
        if ble := tuya_device.ble_device:
            data["function"] = copy.deepcopy(
                {
                    code: {"dp_id": f.dp_id, "type": str(f.type), "values": f.values}
                    for code, f in (ble.function or {}).items()
                }
            )
            data["status_range"] = copy.deepcopy(
                {
                    code: {"dp_id": f.dp_id, "type": str(f.type), "values": f.values}
                    for code, f in (ble.status_range or {}).items()
                }
            )
            data["status"] = copy.deepcopy(
                {
                    str(dp.id): {
                        "value": (
                            dp.value
                            if not isinstance(dp.value, bytes)
                            else dp.value.hex()
                        ),
                        "type": str(dp.type),
                        "timestamp": dp.timestamp,
                    }
                    for dp in ble.datapoints.values()
                }
            )
            # Merge BLE function/status_range into cloud_spec.dps for
            # a unified view regardless of transport.
            cloud_spec["dps"] = copy.deepcopy(data.get("function", {}))
            cloud_spec["dps"].update(copy.deepcopy(data.get("status_range", {})))
        break
    return data


def obfuscate(key, start_characters=3, end_characters=3) -> str:
    """Return obfuscated text by removing characters between [start_characters and end_characters]"""
    if start_characters <= 0 and end_characters <= 0:
        return ""

    return f"{key[0:start_characters]}...{key[-end_characters:]}"
