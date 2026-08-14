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


def _fake_event_wrapper(event_data):
    """Build a minimal event wrapper returning a fixed read result."""

    class _Wrapper:
        options = ["single_click", "double_click"]

        def skip_update(self, device, updated, timestamps=None):
            return False

        def read_device_status(self, device):
            return event_data

    return _Wrapper()


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


async def test_event_entity_process_device_update_triggers():
    """DP-driven events fire from _process_device_update (core parity)."""
    device = await init(CONFIG, EVENT_DOMAIN, LocalTuyaEvent)
    entity: LocalTuyaEvent = get_entites(device)[0]
    entity._dpcode_wrapper = _fake_event_wrapper(("single_click", None))
    entity._attr_event_types = entity._dpcode_wrapper.options

    assert await entity._process_device_update(["switch_mode1"], None) is True
    assert _last_event_type(entity) == "single_click"


async def test_event_entity_process_device_update_skips_without_data():
    device = await init(CONFIG, EVENT_DOMAIN, LocalTuyaEvent)
    entity: LocalTuyaEvent = get_entites(device)[0]
    entity._dpcode_wrapper = _fake_event_wrapper(None)
    entity._attr_event_types = entity._dpcode_wrapper.options

    assert await entity._process_device_update(["switch_mode1"], None) is False
    assert _last_event_type(entity) is None
