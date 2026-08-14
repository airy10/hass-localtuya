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
