"""Test for localtuya."""

from unittest.mock import PropertyMock, patch

from . import *
from custom_components.localtuya import coordinator
from custom_components.localtuya.const import DPType
from custom_components.localtuya.light import (
    LocalTuyaLight,
    DOMAIN as PLATFORM_DOMAIN,
    ColorMode,
)

CONFIG = {
    DEVICE_NAME: {
        **DEVICE_CONFIG,
        "entities": [
            {
                "id": "20",
                "color_mode": "21",
                "brightness": "22",
                "color_temp": "23",
                "color": "24",
                "scene": "25",
                "brightness_lower": 0,
                "brightness_upper": 1000,
                "color_temp_min_kelvin": 2700,
                "color_temp_max_kelvin": 6500,
                "color_temp_reverse": False,
                "music_mode": True,
                "friendly_name": None,
                "icon": "",
                "entity_category": "None",
                "platform": "light",
            }
        ],
    }
}

DPS_STATUS = {
    "20": True,
    "21": "white",
    "22": 600,
    "23": 1000,
    "24": "000403e8000c",
    "25": "010e0d000084000003e800000000",
}
ENC_COLOR = "0319090087db1c"
BLE_COLOR = "0319090087db1c"


async def test_light():
    device = await init(CONFIG, PLATFORM_DOMAIN, LocalTuyaLight)
    entities: list[LocalTuyaLight] = get_entites(device)

    assert len(entities) > 0
    entity_1, *_ = entities
    assert type(entity_1) is LocalTuyaLight

    status = DPS_STATUS.copy()
    device.status_updated(status)

    assert entity_1.state == "on"
    assert entity_1.brightness is not None
    assert entity_1.is_white_mode
    assert entity_1.color_temp_kelvin is not None

    device.status_updated({"22": 1000})
    assert entity_1.brightness == 255
    device.status_updated({"22": 0})
    assert entity_1.brightness == 0

    device.status_updated({"21": "colour"})
    assert entity_1.hs_color is not None

    device.status_updated({"24": ENC_COLOR})
    sat, brightness = entity_1.hs_color
    assert sat < 360 and brightness <= 100

    device.status_updated({"21": "music"})
    assert entity_1.is_music_mode

    device.status_updated({"21": "scene"})
    assert entity_1.effect is not None
    assert entity_1.is_scene_mode

    # Bluetooth
    # device.status_updated({"21": "colour", "24": "AHhkZA==", "25": ""})


def test_light_description_driven_resolution():
    """A category-table description resolves core wrappers by dpcode."""
    from types import SimpleNamespace

    from custom_components.localtuya.core.dp_wrappers import DPCodeBooleanWrapper
    from custom_components.localtuya.core.dp_wrapper_decorators import (
        BrightnessWrapper,
        ColorTempWrapper,
        StringColorWrapper,
    )
    from custom_components.localtuya.core.ha_entities.base import DPCode, LocalTuyaEntity
    from custom_components.localtuya.entity import entity_config_from_description

    specs = {
        "switch_led": {"dp_id": 1, "type": "Boolean", "values": None},
        "bright_value": {
            "dp_id": 2,
            "type": "Integer",
            "values": {"min": 0, "max": 1000, "scale": 0, "step": 1},
        },
        "work_mode": {
            "dp_id": 3,
            "type": "Enum",
            "values": {"range": ["white", "colour", "scene"]},
        },
        "colour_data": {"dp_id": 4, "type": "String", "values": None},
        "temp_value": {
            "dp_id": 5,
            "type": "Integer",
            "values": {"min": 0, "max": 1000, "scale": 0, "step": 1},
        },
    }
    device = SimpleNamespace(
        function={},
        status_range=specs,
        status={},
        color_data_spec=None,
        white_mode_supported=True,
        is_write_only=False,
        id="dev1",
        product_id="prod-1",
        hass=None,
    )
    desc = LocalTuyaEntity(
        id=DPCode.SWITCH_LED,
        name=None,
        color_mode=DPCode.WORK_MODE,
        brightness=(DPCode.BRIGHT_VALUE_V2, DPCode.BRIGHT_VALUE),
        color_temp=(DPCode.TEMP_VALUE_V2, DPCode.TEMP_VALUE),
        color=(DPCode.COLOUR_DATA_V2, DPCode.COLOUR_DATA),
    )
    config, dp_id = entity_config_from_description(device, desc, "light")

    entity = LocalTuyaLight(
        device,
        {**DEVICE_CONFIG, "entities": []},
        dp_id,
        description=desc,
        config=config,
        add_entites_callback=None,
    )

    assert entity._switch_wrapper is not None
    assert isinstance(entity._switch_wrapper, DPCodeBooleanWrapper)
    assert isinstance(entity._brightness_wrapper, BrightnessWrapper)
    assert isinstance(entity._color_temp_wrapper, ColorTempWrapper)
    assert isinstance(entity._color_data_wrapper, StringColorWrapper)
    assert entity._switch_wrapper.dpcode == DPCode.SWITCH_LED
    assert entity._brightness_wrapper._inner.dpcode == DPCode.BRIGHT_VALUE
    assert entity._color_data_wrapper._inner.dpcode == DPCode.COLOUR_DATA


async def test_light_brightness_from_color_data_is_0_255():
    """Color-data brightness is normalized to HA 0..255 by the wrapper."""
    device = await init(CONFIG, PLATFORM_DOMAIN, LocalTuyaLight)
    entity = get_entites(device)[0]

    # colour mode with a v2 colour_data whose raw V channel is 1000 (full).
    device.status_updated({"21": "colour", "24": "000403e803e8"})
    assert entity.is_color_mode
    assert entity.brightness == 255

    # raw V channel 500 -> HA 128 (via the 0..1000 device range).
    device.status_updated({"24": "000403e801f4"})
    assert entity.brightness == 128


async def test_work_mode_cloud_derivation():
    """US "color" and "dynamic_mod" work_mode values classify via cloud range."""
    with patch.object(
        coordinator.TuyaDevice,
        "status_range",
        new_callable=PropertyMock,
        return_value={
            "work_mode": {
                "type": DPType.ENUM,
                "values": {"0": "color", "1": "dynamic_mod", "2": "scene_mod"},
                "dp_id": 21,
            }
        },
    ):
        device = await init(CONFIG, PLATFORM_DOMAIN, LocalTuyaLight)
    entities: list[LocalTuyaLight] = get_entites(device)

    assert len(entities) > 0
    entity_1, *_ = entities

    device.status_updated({"21": "color"})
    assert entity_1.is_color_mode
    assert not entity_1.is_music_mode
    assert not entity_1.is_white_mode

    device.status_updated({"21": "dynamic_mod"})
    assert entity_1.is_music_mode
    assert not entity_1.is_color_mode

    device.status_updated({"21": "scene_mod"})
    assert entity_1.is_scene_mode
    assert not entity_1.is_color_mode
