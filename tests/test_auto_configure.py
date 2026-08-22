from . import *
from custom_components.localtuya.core.ha_entities import (
    DATA_PLATFORMS,
    category_has_descriptions,
)
from custom_components.localtuya.const import (
    PLATFORMS,
    CONF_NO_CLOUD,
    DEVICE_CLOUD_DATA,
    CONF_BLE_ADDRESS,
    CONF_NODE_ID,
)
from custom_components.localtuya.config_flow import (
    LocalTuyaOptionsFlowHandler,
    NO_ADDITIONAL_ENTITIES,
    devices_schema,
)


def test_platforms_have_category_tables():
    for k in PLATFORMS.values():
        assert k in DATA_PLATFORMS


def test_category_has_descriptions():
    assert category_has_descriptions("kg")  # switch
    assert category_has_descriptions("cl")  # cover
    assert not category_has_descriptions("not_a_category")


class _FakeCloud:
    def __init__(self, device_list):
        self.device_list = device_list
        self.async_get_device_functions = AsyncMock(return_value={})


class _FakeConfigEntry:
    def __init__(self):
        self.data = {CONF_NO_CLOUD: False, "devices": {}}


async def test_auto_configure_device_stores_cloud_data_and_empty_entities(
    monkeypatch,
):
    """Auto-configure persists cloud specs + empty entities (definition-driven)."""
    flow = LocalTuyaOptionsFlowHandler.__new__(LocalTuyaOptionsFlowHandler)
    entry = _FakeConfigEntry()
    cloud = _FakeCloud({"dev1": {"category": "kg", "product_id": "x", "dps_data": {}}})
    monkeypatch.setattr(
        LocalTuyaOptionsFlowHandler, "config_entry", property(lambda self: entry)
    )
    monkeypatch.setattr(
        LocalTuyaOptionsFlowHandler, "cloud_data", property(lambda self: cloud)
    )
    flow.selected_device = "dev1"
    flow.device_data = {"device_id": "dev1", "friendly_name": "Lamp"}
    captured = {}

    async def fake_pick_entity_type(user_input):
        captured["user_input"] = user_input
        captured["entities"] = flow.entities
        return {"type": "create_entry"}

    flow.async_step_pick_entity_type = fake_pick_entity_type

    result = await flow.async_step_auto_configure_device()

    assert result["type"] == "create_entry"
    assert captured["user_input"] == {NO_ADDITIONAL_ENTITIES: True}
    assert captured["entities"] == []
    assert flow.device_data[DEVICE_CLOUD_DATA]["category"] == "kg"


def test_devices_schema_displays_ble_devices_without_host():
    """BLE devices (no CONF_HOST) must not crash edit_device's device picker."""
    ble_dev = {
        CONF_BLE_ADDRESS: "AA:BB:CC:DD:EE:FF",
        CONF_NODE_ID: None,
        "entities": [],
    }
    eth_dev = {"host": "192.168.1.5", CONF_NODE_ID: None, "entities": []}
    sub_dev = {CONF_NODE_ID: "node1", "entities": []}

    devices = {}
    for dev_id, configured_dev in {
        "dev_ble": ble_dev,
        "dev_eth": eth_dev,
        "dev_sub": sub_dev,
    }.items():
        if configured_dev.get(CONF_NODE_ID, None):
            devices[dev_id] = "Sub Device"
        else:
            devices[dev_id] = configured_dev.get(
                "host", configured_dev.get(CONF_BLE_ADDRESS, "")
            )

    assert devices == {
        "dev_ble": "AA:BB:CC:DD:EE:FF",
        "dev_eth": "192.168.1.5",
        "dev_sub": "Sub Device",
    }

    schema = devices_schema(
        devices, {}, add_custom_device=False, existed_devices={"dev_ble": ble_dev}
    )
    options = schema.schema["selected_device"].config["options"]
    assert "dev_ble (AA:BB:CC:DD:EE:FF)" in [opt["label"] for opt in options]


def _enum_values(*options):
    return '{"type":"Enum","range":[%s]}' % ",".join(f'"{o}"' for o in options)


def test_preview_items_variant_gating_picks_one_select():
    """Only the power_on_behavior variant matching the DP value range shows."""
    from custom_components.localtuya.config_flow import auto_config_preview_items

    dps = {
        "1": {"code": "switch_1", "values": '{"type":"Boolean"}'},
        "2": {"code": "countdown_1", "values": '{"type":"Integer","max":86400}'},
        "3": {"code": "relay_status", "values": _enum_values("on", "off", "memory")},
        "7": {"code": "child_lock", "values": '{"type":"Boolean"}'},
    }
    items = auto_config_preview_items("cz", dps)
    selects = [i for i in items if i.strip().split(" ", 1)[1].startswith("select:")]
    assert selects == ["  • select: Power-on behavior"]

    names = [i.split(": ", 1)[1] for i in items]
    assert len(names) == len(set(names))


def test_preview_items_fallback_variant_always_applies():
    """The ungated relay_status variant covers unknown/missing value ranges."""
    from custom_components.localtuya.config_flow import auto_config_preview_items

    for values in (_enum_values("gibberish"), ""):
        dps = {"3": {"code": "relay_status", "values": values}}
        items = auto_config_preview_items("cz", dps)
        assert any("select" in i and "Power-on behavior" in i for i in items)


def test_preview_items_skips_unknown_dps_and_empty_category():
    """DPs absent from the cloud spec produce no items; unknown categories neither."""
    from custom_components.localtuya.config_flow import auto_config_preview_items

    dps = {
        "3": {"code": "relay_status", "values": _enum_values("power_on")},
        "9": {"code": "cur_current", "values": ""},
    }
    items = auto_config_preview_items("cz", dps)
    # cur_current is present but has an empty values string; sensors gated on
    # it are still listed (no contains_any gate on those rows).
    assert any(i.startswith("  • sensor") for i in items)

    assert auto_config_preview_items("no_such_category", dps) == []
