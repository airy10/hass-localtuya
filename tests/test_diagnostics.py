"""Test for localtuya diagnostics."""

import copy
import inspect
from unittest.mock import AsyncMock

from . import *
from homeassistant.helpers.device_registry import DeviceEntry

from custom_components.localtuya import diagnostics, HassLocalTuyaData
from custom_components.localtuya.const import DOMAIN, TRANSPORT_BLE
from custom_components.localtuya.coordinator import TuyaDevice


class MockFunction:
    def __init__(self, dp_id, type_, values):
        self.dp_id = dp_id
        self.type = type_
        self.values = values


class MockDP:
    def __init__(self, id_, value, type_, timestamp):
        self.id = id_
        self.value = value
        self.type = type_
        self.timestamp = timestamp


class MockBLE:
    def __init__(self):
        self.function = {"switch": MockFunction(1, "Boolean", {})}
        self.status_range = {"switch": MockFunction(1, "Boolean", {})}
        self.datapoints = type(
            "DPs", (), {"values": lambda self: [MockDP(1, True, "Boolean", 123.0)]}
        )()


def _make_entry():
    entry_data = create_entry(_make_config())
    entry_data["domain"] = "localtuya"
    if "subentries_data" in inspect.signature(ConfigEntry).parameters:
        entry_data["subentries_data"] = None
    return ConfigEntry(**entry_data)


def _make_config():
    return {
        DEVICE_CONFIG["device_id"]: {
            **DEVICE_CONFIG,
            "entities": [
                {
                    "entity_category": "None",
                    "friendly_name": "Switch 1",
                    "icon": "",
                    "id": "1",
                    "platform": "switch",
                    "restore_on_reconnect": False,
                },
            ],
        }
    }


async def test_device_diagnostics_surfaces_ble_spec_and_status():
    hass = HomeAssistant("")
    entry = _make_entry()
    hass.data.setdefault(DOMAIN, {entry.entry_id: {}})
    dev_id = "767823809c9c1f458745"
    tuya_device = TuyaDevice(hass, entry, _make_config()[DEVICE_CONFIG["device_id"]])
    tuya_device.id = dev_id
    tuya_device._device_config.transport = TRANSPORT_BLE
    tuya_device._interface = type("Iface", (), {"ble_device": MockBLE()})()
    hass.data[DOMAIN][entry.entry_id] = HassLocalTuyaData(
        AsyncMock(), {dev_id: tuya_device}
    )
    hass.data[DOMAIN].setdefault("discovery", None)

    dev_entry = DeviceEntry(
        identifiers={("localtuya", f"localtuya_{dev_id}")},
        config_entry_id=entry.entry_id,
    )

    data = await diagnostics.async_get_device_diagnostics(hass, entry, dev_entry)

    assert data["function"]["switch"]["dp_id"] == 1
    assert data["function"]["switch"]["type"] == "Boolean"
    assert data["status_range"]["switch"]["dp_id"] == 1
    assert data["status"]["1"]["value"] is True
    assert data["status"]["1"]["type"] == "Boolean"
    assert data["status"]["1"]["timestamp"] == 123.0


async def test_device_diagnostics_skips_when_no_ble_device():
    hass = HomeAssistant("")
    entry = _make_entry()
    hass.data.setdefault(DOMAIN, {entry.entry_id: {}})
    dev_id = "767823809c9c1f458745"
    tuya_device = TuyaDevice(hass, entry, _make_config()[DEVICE_CONFIG["device_id"]])
    tuya_device.id = dev_id

    hass.data[DOMAIN][entry.entry_id] = HassLocalTuyaData(
        AsyncMock(), {dev_id: tuya_device}
    )
    hass.data[DOMAIN].setdefault("discovery", None)

    dev_entry = DeviceEntry(
        identifiers={("localtuya", f"localtuya_{dev_id}")},
        config_entry_id=entry.entry_id,
    )

    data = await diagnostics.async_get_device_diagnostics(hass, entry, dev_entry)

    assert "function" not in data
    assert "status_range" not in data
    assert "status" not in data
    assert data["device_config"] is not None
