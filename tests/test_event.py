"""Test for localtuya event platform."""

from . import *
from homeassistant.const import CONF_DEVICE_ID

from custom_components.localtuya.event import LocalTuyaEvent, DOMAIN as EVENT_DOMAIN

CONFIG = {
    DEVICE_NAME: {
        **DEVICE_CONFIG,
        "entities": [
            {
                "entity_category": "None",
                "friendly_name": "Event 1",
                "icon": "",
                "id": "1",
                "platform": "event",
                "restore_on_reconnect": False,
            },
        ],
    }
}


def _last_event_type(entity) -> str | None:
    return entity._EventEntity__last_event_type


async def test_event_entity_ignores_other_devices():
    device = await init(CONFIG, EVENT_DOMAIN, LocalTuyaEvent)
    entity: LocalTuyaEvent = get_entites(device)[0]

    await entity._handle_fingerbot_button_event(
        type("Event", (), {"data": {CONF_DEVICE_ID: "other-device"}})()
    )
    assert _last_event_type(entity) is None


async def test_event_entity_triggers_for_own_device():
    device = await init(CONFIG, EVENT_DOMAIN, LocalTuyaEvent)
    entity: LocalTuyaEvent = get_entites(device)[0]

    await entity._handle_fingerbot_button_event(
        type("Event", (), {"data": {CONF_DEVICE_ID: entity._device_config.id}})()
    )
    assert _last_event_type(entity) == "pressed"
