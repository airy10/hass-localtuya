"""Test for localtuya valve."""

from . import *
from custom_components.localtuya.valve import LocalTuyaValve, DOMAIN as VALVE_DOMAIN

CONFIG = {
    DEVICE_NAME: {
        **DEVICE_CONFIG,
        "entities": [
            {
                "entity_category": "None",
                "friendly_name": "Valve 1",
                "icon": "",
                "id": "1",
                "platform": "valve",
                "restore_on_reconnect": False,
            },
            {
                "entity_category": "None",
                "friendly_name": "Valve 2",
                "icon": "",
                "id": "2",
                "platform": "valve",
                "restore_on_reconnect": False,
            },
        ],
    }
}

DPS_STATUS = {"1": True, "2": False}


async def test_valve():
    device = await init(CONFIG, VALVE_DOMAIN, LocalTuyaValve)
    entities: list[LocalTuyaValve] = get_entites(device)

    assert len(entities) > 0
    entity_valve1, entity_valve2, *_ = entities
    assert type(entity_valve1) is LocalTuyaValve

    assert entity_valve1.is_closed is None
    device.status_updated(DPS_STATUS)

    assert entity_valve1.is_closed is False  # open
    assert entity_valve2.is_closed is True  # closed