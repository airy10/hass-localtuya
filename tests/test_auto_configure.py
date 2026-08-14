from . import *
from custom_components.localtuya.core.ha_entities import (
    DATA_PLATFORMS,
    category_has_descriptions,
)
from custom_components.localtuya.const import PLATFORMS, CONF_NO_CLOUD, DEVICE_CLOUD_DATA
from custom_components.localtuya.config_flow import (
    LocalTuyaOptionsFlowHandler,
    NO_ADDITIONAL_ENTITIES,
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
    cloud = _FakeCloud(
        {"dev1": {"category": "kg", "product_id": "x", "dps_data": {}}}
    )
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
