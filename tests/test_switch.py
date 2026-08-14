"""Test for localtuya."""

from . import *
from homeassistant.const import EntityCategory
from custom_components.localtuya.switch import LocalTuyaSwitch, DOMAIN as SWITCH_DOMAIN

CONFIG = {
    DEVICE_NAME: {
        **DEVICE_CONFIG,
        "entities": [
            {
                "entity_category": "None",
                "friendly_name": "Switch 1",
                "icon": "",
                "id": "1",
                "is_passive_entity": False,
                "platform": "switch",
                "restore_on_reconnect": False,
            },
            {
                "entity_category": "config",
                "friendly_name": "Switch 2",
                "icon": "",
                "id": "2",
                "is_passive_entity": False,
                "platform": "switch",
                "restore_on_reconnect": False,
            },
        ],
    }
}

DPS_STATUS = {"1": True, "2": False}


async def test_switch():
    device = await init(CONFIG, SWITCH_DOMAIN, LocalTuyaSwitch)
    entities: list[LocalTuyaSwitch] = get_entites(device)

    assert len(entities) > 0
    entity_sw1, entity_sw2, *_ = entities
    assert type(entity_sw1) is LocalTuyaSwitch

    assert entity_sw1.state == None
    device.status_updated(DPS_STATUS)

    assert entity_sw1.state == "on"
    assert entity_sw2.state == "off"
    assert entity_sw2.entity_category == EntityCategory.CONFIG


async def test_switch_bitmap_mask():
    """Bitmap-masked switch reads only masked bits and preserves others."""
    cfg = {
        DEVICE_NAME: {
            **DEVICE_CONFIG,
            "entities": [
                {
                    "entity_category": "None",
                    "friendly_name": "BM Switch",
                    "icon": "",
                    "id": "1",
                    "is_passive_entity": False,
                    "platform": "switch",
                    "restore_on_reconnect": False,
                    "bitmap_mask": "01",
                }
            ],
        }
    }
    device = await init(cfg, SWITCH_DOMAIN, LocalTuyaSwitch)
    entity = get_entites(device)[0]

    device.status_updated({"1": b"\x00"})
    assert entity.is_on is False
    # A bit outside the mask does not turn the switch on.
    device.status_updated({"1": b"\x02"})
    assert entity.is_on is False
    device.status_updated({"1": b"\x03"})
    assert entity.is_on is True

    # Turning on ORs the mask into the current value (0x02 | 0x01 = 0x03).
    with patch.object(entity._device, "set_dp") as set_dp:
        await entity.async_turn_on()
        set_dp.assert_called_once_with(b"\x03", "1")

    # Turning off clears the masked bit and keeps the rest (0x03 & ~0x01).
    with patch.object(entity._device, "set_dp") as set_dp:
        await entity.async_turn_off()
        set_dp.assert_called_once_with(b"\x02", "1")


def test_switch_description_driven_resolution():
    """A category-table description resolves the wrapper by dpcode."""
    from types import SimpleNamespace

    from custom_components.localtuya.core.dp_wrappers import DPCodeBooleanWrapper
    from custom_components.localtuya.core.ha_entities.base import DPCode, LocalTuyaEntity
    from custom_components.localtuya.entity import entity_config_from_description

    device = SimpleNamespace(
        function={"switch_led": {"dp_id": 1, "type": "Boolean", "values": None}},
        status_range={},
        status={},
        id="dev1",
        product_id="prod-1",
        hass=None,
    )
    desc = LocalTuyaEntity(id=DPCode.SWITCH_LED, name="Light Switch")
    config, dp_id = entity_config_from_description(device, desc, "switch")

    entity = LocalTuyaSwitch(
        device,
        {**DEVICE_CONFIG, "entities": []},
        dp_id,
        description=desc,
        config=config,
        add_entites_callback=None,
    )

    assert entity._dpcode_wrapper is not None
    assert isinstance(entity._dpcode_wrapper, DPCodeBooleanWrapper)
    assert entity._dpcode_wrapper.dpcode == DPCode.SWITCH_LED


async def test_switch_auto_created_from_cloud_category():
    """A device with a cloud category and no manual entities auto-creates a switch."""
    from custom_components.localtuya.core.dp_wrappers import DPCodeBooleanWrapper

    cfg = {
        DEVICE_NAME: {
            **DEVICE_CONFIG,
            "entities": [],
            "device_cloud_data": {
                "category": "kg",
                "dps_data": {
                    "1": {"code": "switch", "type": "Boolean", "values": None},
                },
            },
        }
    }
    device = await init(cfg, SWITCH_DOMAIN, LocalTuyaSwitch)
    entities = get_entites(device)

    assert len(entities) == 1
    entity = entities[0]
    assert isinstance(entity._dpcode_wrapper, DPCodeBooleanWrapper)
    assert entity._dpcode_wrapper.dpcode == "switch"
