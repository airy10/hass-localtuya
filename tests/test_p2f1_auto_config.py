"""Tests for auto-configuration (per-product mapping + unified entity resolver)."""

from homeassistant.const import Platform

from custom_components.localtuya.core.mappings import (
    MAPPINGS,
    TuyaCategoryMapping,
    TuyaEntityMapping,
    get_mapping_by_device,
)
from custom_components.localtuya.entity import (
    _auto_entities_for_device,
    _entity_specs_for_device,
)


class MockDatapoints:
    def __init__(self, ids):
        self._ids = set(ids)

    def has_id(self, dp_id, type=None):
        return dp_id in self._ids


class MockBleDevice:
    def __init__(self, category, product_id, dp_ids):
        self.category = category
        self.product_id = product_id
        self.datapoints = MockDatapoints(dp_ids)


class MockSpecFn:
    def __init__(self, dp_id):
        self.dp_id = dp_id


class MockTuyaDevice:
    def __init__(self, ble_device=None, category=None, function=None, status_range=None):
        self._ble = ble_device
        self.category = category
        self.function = function or {}
        self.status_range = status_range or {}

    @property
    def ble_device(self):
        return self._ble


def test_get_mapping_by_device_known_product():
    device = MockBleDevice("co2bj", "59s19z5m", set())
    mappings = get_mapping_by_device(device)
    assert len(mappings) == 7
    assert all(m.platform in (Platform.SENSOR, Platform.SWITCH) for m in mappings)


def test_get_mapping_by_device_unknown_product_empty():
    device = MockBleDevice("co2bj", "unknown", set())
    assert get_mapping_by_device(device) == []


def test_get_mapping_by_device_unknown_category():
    device = MockBleDevice("nope", "x", set())
    assert get_mapping_by_device(device) == []


def test_auto_entities_force_add_and_has_id_gating():
    MAPPINGS["testcat"] = TuyaCategoryMapping(
        products={
            "testprod": [
                TuyaEntityMapping(
                    dp_id=1,
                    platform=Platform.SENSOR,
                    config={"friendly_name": "Always"},
                    force_add=True,
                ),
                TuyaEntityMapping(
                    dp_id=2,
                    platform=Platform.SENSOR,
                    config={"friendly_name": "Present"},
                    force_add=False,
                ),
                TuyaEntityMapping(
                    dp_id=3,
                    platform=Platform.SENSOR,
                    config={"friendly_name": "Absent"},
                    force_add=False,
                ),
            ]
        }
    )
    device = MockTuyaDevice(MockBleDevice("testcat", "testprod", {1, 2}))
    dev_entry = {}
    entities = _auto_entities_for_device(device, "sensor", dev_entry)
    assert [e["id"] for e in entities] == ["1", "2"]
    assert len(dev_entry["entities"]) == 2


def test_auto_entities_platform_filter():
    device = MockTuyaDevice(MockBleDevice("co2bj", "59s19z5m", {1, 2, 11, 13}))
    dev_entry = {}
    sensors = _auto_entities_for_device(device, "sensor", dev_entry)
    switches = _auto_entities_for_device(device, "switch", dev_entry)
    assert all(e["platform"] == "sensor" for e in sensors)
    assert all(e["platform"] == "switch" for e in switches)
    assert len(sensors) == 4
    assert len(switches) == 3


def test_auto_entities_non_ble_returns_empty():
    device = MockTuyaDevice(None)
    assert _auto_entities_for_device(device, "sensor", {}) == []


def test_auto_entities_injects_config_id_and_platform():
    device = MockTuyaDevice(MockBleDevice("co2bj", "59s19z5m", {2}))
    dev_entry = {}
    entities = _auto_entities_for_device(device, "sensor", dev_entry)
    for e in entities:
        assert e["id"] == str(e["dp_id"]) if "dp_id" in e else "id" in e
        assert e["platform"] == "sensor"


# --- unified resolver (_entity_specs_for_device) ---


def test_entity_specs_for_device_ble_per_product_first():
    device = MockTuyaDevice(
        MockBleDevice("co2bj", "59s19z5m", {1, 2, 11, 13}),
        category="co2bj",
    )
    specs = _entity_specs_for_device(device, "sensor", {})
    assert specs
    assert all(description is None for _, description in specs)


def test_entity_specs_for_device_ble_falls_back_to_category_tables():
    device = MockTuyaDevice(
        MockBleDevice("kg", "unknown", set()),
        category="kg",
        status_range={"switch": {"dp_id": 1, "type": "Boolean", "values": None}},
    )
    specs = _entity_specs_for_device(device, "switch", {})
    assert specs
    assert all(description is not None for _, description in specs)


def test_entity_specs_for_device_ethernet_uses_category_tables():
    device = MockTuyaDevice(
        None,
        category="kg",
        status_range={"switch": {"dp_id": 1, "type": "Boolean", "values": None}},
    )
    specs = _entity_specs_for_device(device, "switch", {})
    assert specs
    assert all(description is not None for _, description in specs)
