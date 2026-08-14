"""Tests for platform wrapper delegation (core-alignment Phases C3-C14).

Each aligned platform resolves cloud-spec wrappers via dp_wrapper_by_id and
delegates reads/writes through them when available, falling back to config
handling when the DP is unknown (wrapper is None). These tests patch
dp_wrapper_by_id with a fake wrapper and verify the delegation paths.
"""

from unittest.mock import patch

from homeassistant.components.cover import ATTR_POSITION

from . import *
from custom_components.localtuya.alarm_control_panel import (
    DOMAIN as ALARM_DOMAIN,
    LocalTuyaAlarmControlPanel,
)
from custom_components.localtuya.binary_sensor import (
    DOMAIN as BS_DOMAIN,
    LocalTuyaBinarySensor,
)
from custom_components.localtuya.button import DOMAIN as BTN_DOMAIN, LocalTuyaButton
from custom_components.localtuya.climate import (
    DOMAIN as CLIMATE_DOMAIN,
    LocalTuyaClimate,
)
from custom_components.localtuya.cover import DOMAIN as COVER_DOMAIN, LocalTuyaCover
from custom_components.localtuya.fan import DOMAIN as FAN_DOMAIN, LocalTuyaFan
from custom_components.localtuya.humidifier import (
    DOMAIN as HUM_DOMAIN,
    LocalTuyaHumidifier,
)
from custom_components.localtuya.light import DOMAIN as LIGHT_DOMAIN, LocalTuyaLight
from custom_components.localtuya.number import DOMAIN as NUM_DOMAIN, LocalTuyaNumber
from custom_components.localtuya.select import DOMAIN as SEL_DOMAIN, LocalTuyaSelect
from custom_components.localtuya.sensor import DOMAIN as SENSOR_DOMAIN, LocalTuyaSensor
from custom_components.localtuya.siren import DOMAIN as SIREN_DOMAIN, LocalTuyaSiren
from custom_components.localtuya.switch import (
    DOMAIN as SWITCH_DOMAIN,
    LocalTuyaSwitch,
)
from custom_components.localtuya.vacuum import (
    DOMAIN as VACUUM_DOMAIN,
    LocalTuyaVacuum,
)


class FakeWrapper:
    """Duck-typed DPCodeWrapper: records sent values, returns a canned read."""

    native_unit: str | None = None
    suggested_unit: str | None = None
    min_value = 1
    max_value = 100
    value_step = 1

    def __init__(self, read_value=None, options=None, dpcode="fake"):
        self.read_value = read_value
        self.options = options
        self.dpcode = dpcode
        self.sent = []

    def read_device_status(self, device):
        return self.read_value

    def get_update_commands(self, device, value):
        self.sent.append(value)
        return [{"code": self.dpcode, "dp_id": 1, "value": value}]

    def skip_update(self, device, updated_status_properties, dp_timestamps=None):
        return self.dpcode not in (updated_status_properties or [])


def _base_config(platform, dpid="1", extra=None):
    cfg = {
        "entity_category": "None",
        "friendly_name": "Test",
        "icon": "",
        "id": dpid,
        "is_passive_entity": False,
        "platform": platform,
        "restore_on_reconnect": False,
    }
    if extra:
        cfg.update(extra)
    return {DEVICE_NAME: {**DEVICE_CONFIG, "entities": [cfg]}}


async def _patch_setup(platform_module, wrapper, config, domain, entity_class):
    with patch.object(platform_module, "dp_wrapper_by_id", return_value=wrapper):
        device = await init(config, domain, entity_class)
    return device, get_entites(device)


async def _expect_write(entity, props):
    """Return whether _process_device_update says the state should be written."""
    return await entity._process_device_update(props, None)


async def test_switch_wrapper_read_write_and_skip():
    """Switch is_on reads the wrapper; turn_on/off send wrapper updates."""
    import custom_components.localtuya.switch as mod

    wrapper = FakeWrapper(read_value=True)
    _, entities = await _patch_setup(
        mod, wrapper, _base_config("switch"), SWITCH_DOMAIN, LocalTuyaSwitch
    )
    entity = entities[0]
    assert entity.is_on is True
    await entity.async_turn_off()
    assert wrapper.sent == [False]
    await entity.async_turn_on()
    assert wrapper.sent == [False, True]
    assert await _expect_write(entity, ["fake"]) is True
    assert await _expect_write(entity, ["other"]) is False


async def test_switch_wrapper_none_falls_back():
    """No wrapper: reads cached state, writes raw DP, never skips."""
    import custom_components.localtuya.switch as mod

    _, entities = await _patch_setup(
        mod, None, _base_config("switch"), SWITCH_DOMAIN, LocalTuyaSwitch
    )
    entity = entities[0]
    assert entity.is_on is None
    with patch.object(entity._device, "set_dp") as set_dp:
        await entity.async_turn_on()
        set_dp.assert_called_once_with(True, "1")
    assert await _expect_write(entity, ["1"]) is True


async def test_sensor_wrapper_read():
    """Sensor native_value reads the wrapper when no scaling/offset."""
    import custom_components.localtuya.sensor as mod

    wrapper = FakeWrapper(read_value=42)
    _, entities = await _patch_setup(
        mod, wrapper, _base_config("sensor"), SENSOR_DOMAIN, LocalTuyaSensor
    )
    assert entities[0].native_value == 42
    assert await _expect_write(entities[0], ["fake"]) is True


async def test_select_wrapper_read_write():
    """Select current_option reads wrapper, async_select_option sends it."""
    import custom_components.localtuya.select as mod

    wrapper = FakeWrapper(read_value="auto", options=["auto", "manual"])
    _, entities = await _patch_setup(
        mod, wrapper, _base_config("select"), SEL_DOMAIN, LocalTuyaSelect
    )
    entity = entities[0]
    assert entity.current_option == "auto"
    await entity.async_select_option("manual")
    assert wrapper.sent == ["manual"]
    assert await _expect_write(entity, ["fake"]) is True


async def test_number_wrapper_read_write():
    """Number native_value/async_set_native_value delegate to wrapper."""
    import custom_components.localtuya.number as mod

    wrapper = FakeWrapper(read_value=25.0)
    _, entities = await _patch_setup(
        mod, wrapper, _base_config("number"), NUM_DOMAIN, LocalTuyaNumber
    )
    entity = entities[0]
    assert entity.native_value == 25.0
    await entity.async_set_native_value(30.0)
    assert wrapper.sent == [30.0]
    assert await _expect_write(entity, ["fake"]) is True


async def test_number_wrapper_scaling_stays_config():
    """Scaling/offset configured: write stays on raw config path."""
    import custom_components.localtuya.number as mod

    wrapper = FakeWrapper(read_value=10.0)
    cfg = _base_config("number", extra={"scaling": "2.0"})
    _, entities = await _patch_setup(mod, wrapper, cfg, NUM_DOMAIN, LocalTuyaNumber)
    entity = entities[0]
    with patch.object(entity._device, "set_dp") as set_dp:
        await entity.async_set_native_value(20.0)
        set_dp.assert_called_once_with(10, "1")
    assert wrapper.sent == []


async def test_fan_wrapper_reads_and_writes():
    """Fan delegates switch/speed reads and writes through wrappers."""
    import custom_components.localtuya.fan as mod

    switch_wrapper = FakeWrapper(read_value=True)
    speed_wrapper = FakeWrapper(read_value=5)

    def by_id(device, dp_id):
        return {"1": switch_wrapper, "2": speed_wrapper}.get(dp_id)

    cfg = _base_config(
        "fan",
        extra={
            "fan_speed_control": "2",
            "fan_speed_min": 1,
            "fan_speed_max": 9,
            "fan_speed_ordered_list": "disabled",
        },
    )
    with patch.object(mod, "dp_wrapper_by_id", side_effect=by_id):
        device = await init(cfg, FAN_DOMAIN, LocalTuyaFan)
    entity = get_entites(device)[0]
    entity.schedule_update_ha_state = lambda: None
    assert entity.is_on is True
    assert entity.percentage == 55  # scale 5 of 1..9 to 1..100
    await entity.async_turn_off()
    assert switch_wrapper.sent == [False]


async def test_light_wrapper_switch_delegation():
    """Light is_on/turn_on/off delegate to the switch wrapper."""
    import custom_components.localtuya.light as mod

    wrapper = FakeWrapper(read_value=True)
    cfg = _base_config(
        "light", extra={"brightness": "2", "color_temp": "3", "color_mode": "4"}
    )
    _, entities = await _patch_setup(mod, wrapper, cfg, LIGHT_DOMAIN, LocalTuyaLight)
    entity = entities[0]
    assert entity.is_on is True
    await entity.async_turn_off()
    assert wrapper.sent == [False]


async def test_siren_wrapper_read_write_and_skip():
    """Siren is_on reads wrapper bool; turn_on/off send wrapper updates."""
    import custom_components.localtuya.siren as mod

    wrapper = FakeWrapper(read_value=True)
    _, entities = await _patch_setup(
        mod,
        wrapper,
        _base_config("siren", extra={"state_on": "true"}),
        SIREN_DOMAIN,
        LocalTuyaSiren,
    )
    entity = entities[0]
    assert entity.is_on is True
    await entity.async_turn_on()
    assert wrapper.sent == [True]
    assert await _expect_write(entity, ["fake"]) is True


async def test_button_wrapper_press():
    """Button async_press sends wrapper update."""
    import custom_components.localtuya.button as mod

    wrapper = FakeWrapper()
    _, entities = await _patch_setup(
        mod, wrapper, _base_config("button"), BTN_DOMAIN, LocalTuyaButton
    )
    await entities[0].async_press()
    assert wrapper.sent == [True]


async def test_binary_sensor_skip_update_gate():
    """Binary sensor state stays config-driven; update gate via wrapper."""
    import custom_components.localtuya.binary_sensor as mod

    wrapper = FakeWrapper()
    _, entities = await _patch_setup(
        mod,
        wrapper,
        _base_config("binary_sensor", extra={"state_on": "true,1"}),
        BS_DOMAIN,
        LocalTuyaBinarySensor,
    )
    entity = entities[0]
    assert await _expect_write(entity, ["fake"]) is True
    assert await _expect_write(entity, ["other"]) is False


async def test_humidifier_wrapper_reads_and_writes():
    """Humidifier delegates all four configured DPs through wrappers."""
    import custom_components.localtuya.humidifier as mod

    switch_wrapper = FakeWrapper(read_value=True)
    target_wrapper = FakeWrapper(read_value=50)
    current_wrapper = FakeWrapper(read_value=48)
    mode_wrapper = FakeWrapper(read_value="auto")

    def by_id(device, dp_id):
        return {
            "1": switch_wrapper,
            "2": target_wrapper,
            "3": current_wrapper,
            "4": mode_wrapper,
        }.get(dp_id)

    cfg = _base_config(
        "humidifier",
        extra={
            "humidifier_set_humidity_dp": "2",
            "humidifier_current_humidity_dp": "3",
            "humidifier_mode_dp": "4",
            "humidifier_available_modes": {"auto": "Auto"},
            "min_humidity": 30,
            "max_humidity": 80,
        },
    )
    with patch.object(mod, "dp_wrapper_by_id", side_effect=by_id):
        device = await init(cfg, HUM_DOMAIN, LocalTuyaHumidifier)
    entity = get_entites(device)[0]
    assert entity.is_on is True
    assert entity.target_humidity == 50
    assert entity.current_humidity == 48
    assert entity.mode == "Auto"
    await entity.async_set_humidity(60)
    assert target_wrapper.sent == [60]
    await entity.async_set_mode("Auto")
    assert mode_wrapper.sent == ["auto"]


async def test_alarm_control_panel_wrapper_read_write():
    """Alarm state reads wrapper; actions send wrapper updates."""
    import custom_components.localtuya.alarm_control_panel as mod

    wrapper = FakeWrapper(read_value="disarmed")
    _, entities = await _patch_setup(
        mod,
        wrapper,
        _base_config(
            "alarm_control_panel",
            extra={
                "alarm_supported_states": {
                    "disarmed": "disarmed",
                    "armed_home": "home",
                    "armed_away": "arm",
                    "triggered": "sos",
                }
            },
        ),
        ALARM_DOMAIN,
        LocalTuyaAlarmControlPanel,
    )
    entity = entities[0]
    assert entity.alarm_state == "disarmed"
    await entity.async_alarm_arm_away()
    assert wrapper.sent == ["arm"]


async def test_climate_wrapper_switch_delegation():
    """Climate _is_on/turn_on/off delegate to the switch wrapper."""
    import custom_components.localtuya.climate as mod

    wrapper = FakeWrapper(read_value=True)
    cfg = _base_config("climate", extra={"hvac_switch_dp": "2", "target_temp_dp": "3"})
    with patch.object(mod, "dp_wrapper_by_id", return_value=wrapper):
        device = await init(cfg, CLIMATE_DOMAIN, LocalTuyaClimate)
    entity = get_entites(device)[0]
    assert entity._is_on is True
    await entity.async_turn_off()
    assert wrapper.sent == [False]


async def test_cover_set_position_wrapper_write():
    """Cover set-position write delegates to the wrapper when configured."""
    import custom_components.localtuya.cover as mod

    wrapper = FakeWrapper()
    cfg = _base_config(
        "cover",
        extra={"positioning_mode": "position", "set_position_dp": "2"},
    )
    with patch.object(mod, "dp_wrapper_by_id", return_value=wrapper):
        device = await init(cfg, COVER_DOMAIN, LocalTuyaCover)
    entity = get_entites(device)[0]
    entity.schedule_update_ha_state = lambda: None
    await entity.async_set_cover_position(**{ATTR_POSITION: 25})
    assert wrapper.sent == [25]


async def test_vacuum_fan_speed_wrapper_read_write():
    """Vacuum fan speed reads/writes delegate to the wrapper."""
    import custom_components.localtuya.vacuum as mod

    wrapper = FakeWrapper(read_value="high")
    cfg = _base_config("vacuum", extra={"powergo_dp": "2", "fan_speed_dp": "3"})
    _, entities = await _patch_setup(
        mod, wrapper, cfg, VACUUM_DOMAIN, LocalTuyaVacuum
    )
    entity = entities[0]
    assert entity.fan_speed == "high"
    await entity.async_set_fan_speed("low")
    assert wrapper.sent == ["low"]