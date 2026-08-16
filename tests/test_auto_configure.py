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
