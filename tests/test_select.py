"""Test for localtuya."""

from unittest.mock import PropertyMock, patch

from . import *
from custom_components.localtuya import coordinator
from custom_components.localtuya.const import DPType
from custom_components.localtuya.select import (
    LocalTuyaSelect,
    DOMAIN as PLATFORM_DOMAIN,
)

CONFIG = {
    DEVICE_NAME: {
        **DEVICE_CONFIG,
        "entities": [
            {
                "entity_category": "config",
                "friendly_name": "Motor Direction",
                "icon": "mdi:swap-vertical",
                "id": "5",
                "is_passive_entity": False,
                "platform": PLATFORM_DOMAIN,
                "restore_on_reconnect": False,
                "select_options": {"back": "Back", "forward": "Forward"},
            }
        ],
    }
}

CONFIG_NO_OPTIONS = {
    DEVICE_NAME: {
        **DEVICE_CONFIG,
        "entities": [
            {
                "entity_category": "config",
                "friendly_name": "Work Mode",
                "id": "5",
                "is_passive_entity": False,
                "platform": PLATFORM_DOMAIN,
                "restore_on_reconnect": False,
            }
        ],
    }
}

DPS_STATUS = {"5": "back"}


async def test_lock():
    device = await init(CONFIG, PLATFORM_DOMAIN, LocalTuyaSelect)
    entities: list[LocalTuyaSelect] = get_entites(device)

    assert len(entities) > 0
    entity_1, *_ = entities
    assert type(entity_1) is LocalTuyaSelect

    device.status_updated(DPS_STATUS)
    assert (
        entity_1.state in CONFIG[DEVICE_NAME]["entities"][0]["select_options"].values()
    )


async def test_cloud_options_fallback():
    """Empty select_options falls back to the cloud enum range (core spec)."""
    with patch.object(
        coordinator.TuyaDevice,
        "status_range",
        new_callable=PropertyMock,
        return_value={
            "work_mode": {
                "type": DPType.ENUM,
                "values": {"0": "color", "1": "white"},
                "dp_id": 5,
            }
        },
    ):
        device = await init(CONFIG_NO_OPTIONS, PLATFORM_DOMAIN, LocalTuyaSelect)
        entities: list[LocalTuyaSelect] = get_entites(device)

        assert len(entities) > 0
        entity_1, *_ = entities
        assert entity_1.options == ["color", "white"]

        device.status_updated({"5": "color"})
        assert entity_1.current_option == "color"
