"""
    This a file contains available tuya data
    https://developer.tuya.com/en/docs/iot/standarddescription?id=K9i5ql6waswzq

    Credits: official HA Tuya integration.
    Modified by: xZetsubou
"""

from .base import (
    DPCode,
    DeviceCategory,
    LocalTuyaEntity,
    CONF_DEVICE_CLASS,
    EntityCategory,
)
from homeassistant.components.switch import SwitchDeviceClass

CHILD_LOCK = (
    LocalTuyaEntity(
        translation_key="child_lock",
        id=DPCode.CHILD_LOCK,
        name="Child Lock",
        icon="mdi:account-lock",
        entity_category=EntityCategory.CONFIG,
    ),
)
SWITCHES: dict[DeviceCategory, tuple[LocalTuyaEntity, ...]] = {
    # White noise machine
    DeviceCategory.BZYD: (
        LocalTuyaEntity(
            translation_key="switch",
            id=DPCode.SWITCH,
        ),
        LocalTuyaEntity(
            translation_key="child_lock",
            id=DPCode.CHILD_LOCK,
            name="Child Lock",
            icon="mdi:account-lock",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="music",
            id=DPCode.SWITCH_MUSIC,
            name="Music",
            icon="mdi:music",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="snooze",
            id=DPCode.SNOOZE,
            name="Snooze",
            icon="mdi:alarm-snooze",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Smart Kettle
    # https://developer.tuya.com/en/docs/iot/fbh?id=K9gf484m21yq7
    DeviceCategory.BH: (
        LocalTuyaEntity(
            translation_key="start",
            id=DPCode.START,
            name="Start",
            icon="mdi:kettle-steam",
        ),
        LocalTuyaEntity(
            translation_key="warm",
            id=DPCode.WARM,
            name="Warm",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # EasyBaby
    # Undocumented, might have a wider use
    DeviceCategory.CN: (
        LocalTuyaEntity(
            translation_key="disinfection",
            id=DPCode.DISINFECTION,
            name="Disinfection",
            icon="mdi:bacteria",
        ),
        LocalTuyaEntity(
            translation_key="water",
            id=DPCode.WATER,
            name="Water",
            icon="mdi:water",
        ),
    ),
    # Smart Odor Eliminator-Pro
    # Undocumented
    DeviceCategory.CWJWQ: (
        LocalTuyaEntity(
            translation_key="switch",
            id=DPCode.SWITCH,
            name="Switch",
        ),
    ),
    # Smart Pet Feeder
    # https://developer.tuya.com/en/docs/iot/categorycwwsq?id=Kaiuz2b6vydld
    DeviceCategory.CWWSQ: (
        LocalTuyaEntity(
            translation_key="slow_feed",
            id=DPCode.SLOW_FEED,
            name="Slow Feed",
            icon="mdi:speedometer-slow",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Pet Water Feeder
    # https://developer.tuya.com/en/docs/iot/f?id=K9gf46aewxem5
    DeviceCategory.CWYSJ: (
        LocalTuyaEntity(
            translation_key="reset_filter",
            id=DPCode.FILTER_RESET,
            name="Reset Filter",
            icon="mdi:filter",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="reset_water_pump",
            id=DPCode.PUMP_RESET,
            name="Reset Water Pump",
            icon="mdi:pump",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="power",
            id=DPCode.SWITCH,
            name="Power",
        ),
        LocalTuyaEntity(
            translation_key="reset_water",
            id=DPCode.WATER_RESET,
            name="Reset Water",
            icon="mdi:water-sync",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="uv_sterilization",
            id=DPCode.UV,
            name="UV Sterilization",
            icon="mdi:lightbulb",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Light
    # https://developer.tuya.com/en/docs/iot/f?id=K9i5ql3v98hn3
    DeviceCategory.DJ: (
        # There are sockets available with an RGB light
        # that advertise as `dj`, but provide an additional
        # switch to control the plug.
        LocalTuyaEntity(
            translation_key="plug",
            id=DPCode.SWITCH,
            name="Plug",
        ),
    ),
    # Electric blanket
    # https://developer.tuya.com/en/docs/iot/categorydr?id=Kaiuz22dyc66p
    DeviceCategory.DR: (
        LocalTuyaEntity(
            translation_key="power",
            id=DPCode.SWITCH,
            name="Power",
            icon="mdi:power",
            device_class=SwitchDeviceClass.SWITCH,
        ),
        LocalTuyaEntity(
            translation_key="side_a_power",
            id=DPCode.SWITCH_1,
            name="Side A Power",
            icon="mdi:alpha-a",
            device_class=SwitchDeviceClass.SWITCH,
        ),
        LocalTuyaEntity(
            translation_key="side_b_power",
            id=DPCode.SWITCH_2,
            name="Side B Power",
            icon="mdi:alpha-b",
            device_class=SwitchDeviceClass.SWITCH,
        ),
        LocalTuyaEntity(
            translation_key="preheat",
            id=DPCode.PREHEAT,
            name="Preheat",
            icon="mdi:radiator",
            device_class=SwitchDeviceClass.SWITCH,
        ),
        LocalTuyaEntity(
            translation_key="side_a_preheat",
            id=DPCode.PREHEAT_1,
            name="Side A Preheat",
            icon="mdi:radiator",
            device_class=SwitchDeviceClass.SWITCH,
        ),
        LocalTuyaEntity(
            translation_key="side_b_preheat",
            id=DPCode.PREHEAT_2,
            name="Side B Preheat",
            icon="mdi:radiator",
            device_class=SwitchDeviceClass.SWITCH,
        ),
    ),
    # Circuit Breaker
    DeviceCategory.DLQ: (
        LocalTuyaEntity(
            translation_key="child_lock",
            id=DPCode.CHILD_LOCK,
            name="Child Lock",
            icon="mdi:account-lock",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="switch",
            id=DPCode.SWITCH,
            name="Switch",
        ),
    ),
    # Wake Up Light II
    # Not documented
    DeviceCategory.HXD: (
        LocalTuyaEntity(
            translation_key="radio",
            id=DPCode.SWITCH_1,
            name="Radio",
            icon="mdi:radio",
        ),
        LocalTuyaEntity(
            translation_key="alarm_2",
            id=DPCode.SWITCH_2,
            name="Alarm 2",
            icon="mdi:alarm",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="alarm_3",
            id=DPCode.SWITCH_3,
            name="Alarm 3",
            icon="mdi:alarm",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="alarm_4",
            id=DPCode.SWITCH_4,
            name="Alarm 4",
            icon="mdi:alarm",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="alarm_5",
            id=DPCode.SWITCH_5,
            name="Alarm 5",
            icon="mdi:alarm",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="alarm_6",
            id=DPCode.SWITCH_6,
            name="Alarm 6",
            icon="mdi:power-sleep",
        ),
    ),
    # Two-way temperature and humidity switch
    # "MOES Temperature and Humidity Smart Switch Module MS-103"
    # Documentation not found
    DeviceCategory.WKCZ: (
        LocalTuyaEntity(
            translation_key="switch_1",
            id=DPCode.SWITCH_1,
            name="Switch 1",
            device_class=SwitchDeviceClass.OUTLET,
        ),
        LocalTuyaEntity(
            translation_key="switch_2",
            id=DPCode.SWITCH_2,
            name="Switch 2",
            device_class=SwitchDeviceClass.OUTLET,
        ),
    ),
    # Switch
    # https://developer.tuya.com/en/docs/iot/s?id=K9gf7o5prgf7s
    DeviceCategory.KG: (
        LocalTuyaEntity(
            translation_key="child_lock",
            id=DPCode.CHILD_LOCK,
            name="Child lock",
            icon="mdi:account-lock",
        ),
        LocalTuyaEntity(
            translation_key="switch",
            id=DPCode.SWITCH,
            name="Switch",
        ),
        LocalTuyaEntity(
            translation_key="switch_1",
            id=DPCode.SWITCH_1,
            name="Switch 1",
        ),
        LocalTuyaEntity(
            translation_key="switch_2",
            id=DPCode.SWITCH_2,
            name="Switch 2",
        ),
        LocalTuyaEntity(
            translation_key="switch_3",
            id=DPCode.SWITCH_3,
            name="Switch 3",
        ),
        LocalTuyaEntity(
            translation_key="switch_4",
            id=DPCode.SWITCH_4,
            name="Switch 4",
        ),
        LocalTuyaEntity(
            translation_key="switch_5",
            id=DPCode.SWITCH_5,
            name="Switch 5",
        ),
        LocalTuyaEntity(
            translation_key="switch_6",
            id=DPCode.SWITCH_6,
            name="Switch 6",
        ),
        LocalTuyaEntity(
            translation_key="switch_7",
            id=DPCode.SWITCH_7,
            name="Switch 7",
        ),
        LocalTuyaEntity(
            translation_key="switch_8",
            id=DPCode.SWITCH_8,
            name="Switch 8",
        ),
        LocalTuyaEntity(
            translation_key="usb",
            id=DPCode.SWITCH_USB1,
            name="USB",
        ),
        LocalTuyaEntity(
            translation_key="usb_2",
            id=DPCode.SWITCH_USB2,
            name="USB 2",
        ),
        LocalTuyaEntity(
            translation_key="usb_3",
            id=DPCode.SWITCH_USB3,
            name="USB 3",
        ),
        LocalTuyaEntity(
            translation_key="usb_4",
            id=DPCode.SWITCH_USB4,
            name="USB 4",
        ),
        LocalTuyaEntity(
            translation_key="usb_5",
            id=DPCode.SWITCH_USB5,
            name="USB 5",
        ),
        LocalTuyaEntity(
            translation_key="usb_6",
            id=DPCode.SWITCH_USB6,
            name="USB 6",
            device_class=SwitchDeviceClass.OUTLET,
        ),
    ),
    # Air Purifier
    # https://developer.tuya.com/en/docs/iot/f?id=K9gf46h2s6dzm
    DeviceCategory.KJ: (
        LocalTuyaEntity(
            translation_key="ionizer",
            id=DPCode.ANION,
            name="Ionizer",
            icon="mdi:minus-circle-outline",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="reset_filter_cartridge",
            id=DPCode.FILTER_RESET,
            name="Reset Filter Cartridge_",
            icon="mdi:filter",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="child_lock",
            id=DPCode.LOCK,
            name="Child Lock",
            icon="mdi:account-lock",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="power",
            id=DPCode.SWITCH,
            name="Power",
        ),
        LocalTuyaEntity(
            translation_key="humidification",
            id=DPCode.WET,
            name="Humidification",
            icon="mdi:water-percent",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="uv_sterilization",
            id=DPCode.UV,
            name="UV Sterilization",
            icon="mdi:minus-circle-outline",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Air conditioner
    # https://developer.tuya.com/en/docs/iot/categorykt?id=Kaiuz0z71ov2n
    DeviceCategory.KT: (
        LocalTuyaEntity(
            translation_key="ionizer",
            id=DPCode.ANION,
            name="Ionizer",
            icon="mdi:minus-circle-outline",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="child_lock",
            id=DPCode.LOCK,
            name="Child Lock",
            icon="mdi:account-lock",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="sleep",
            id=DPCode.SLEEP,
            name="Sleep",
            icon="mdi:sleep",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="shake",
            id=DPCode.SHAKE,
            name="Shake",
            # icon="mdi:vibrate",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="inner_dry",
            id=DPCode.INNERDRY,
            name="Inner Dry",
            icon="mdi:water-outline",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Cat litter box
    # https://developer.tuya.com/en/docs/iot/f?id=Kakg309qkmuit
    DeviceCategory.MSP: (
        LocalTuyaEntity(
            translation_key="auto_clean",
            id=DPCode.AUTO_CLEAN,
            name="Auto Clean",
            icon="mdi:auto-fix",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="switch",
            id=DPCode.SWITCH,
        ),
        LocalTuyaEntity(
            translation_key="manual_cleaning",
            id=DPCode.MANUAL_CLEAN,
            name="Manual Cleaning",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="cleaning",
            id=DPCode.CLEANING,
            name="Cleaning",
            icon="mdi:power",
        ),
        LocalTuyaEntity(
            translation_key="sleep",
            id=DPCode.SLEEPING,
            name="Sleep",
            icon="mdi:sleep",
        ),
        LocalTuyaEntity(
            translation_key="beep",
            id=DPCode.BEEP,
            name="Beep",
            icon="mdi:volume-high",
        ),
        LocalTuyaEntity(
            translation_key="light_indicator",
            id=DPCode.INDICATOR_LIGHT,
            name="Light Indicator",
            icon="mdi:wall-sconce-flat-variant",
        ),
        LocalTuyaEntity(
            translation_key="enable_quiet_timing",
            id=DPCode.QUIET_TIMING_ON,
            name="Enable Quiet Timing",
            icon="mdi:timer-settings-outline",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Po
    # Sous Vide Cooker
    # https://developer.tuya.com/en/docs/iot/categorymzj?id=Kaiuz2vy130ux
    DeviceCategory.MZJ: (
        LocalTuyaEntity(
            translation_key="switch",
            id=DPCode.SWITCH,
            name="Switch",
            icon="mdi:power",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="start",
            id=DPCode.START,
            name="Start",
            icon="mdi:pot-steam",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Power Socket
    # https://developer.tuya.com/en/docs/iot/s?id=K9gf7o5prgf7s
    DeviceCategory.PC: (
        LocalTuyaEntity(
            translation_key="child_lock",
            id=DPCode.CHILD_LOCK,
            name="Child Lock",
            icon="mdi:account-lock",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="overcharge",
            id=DPCode.OVERCHARGE_SWITCH,
            name="Overcharge",
            icon="mdi:flash-alert",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="switch_1",
            id=DPCode.SWITCH_1,
            name="Switch 1",
            device_class=SwitchDeviceClass.OUTLET,
        ),
        LocalTuyaEntity(
            translation_key="switch_2",
            id=DPCode.SWITCH_2,
            name="Switch 2",
            device_class=SwitchDeviceClass.OUTLET,
        ),
        LocalTuyaEntity(
            translation_key="switch_3",
            id=DPCode.SWITCH_3,
            name="Switch 3",
            device_class=SwitchDeviceClass.OUTLET,
        ),
        LocalTuyaEntity(
            translation_key="switch_4",
            id=DPCode.SWITCH_4,
            name="Switch 4",
            device_class=SwitchDeviceClass.OUTLET,
        ),
        LocalTuyaEntity(
            translation_key="switch_5",
            id=DPCode.SWITCH_5,
            name="Switch 5",
            device_class=SwitchDeviceClass.OUTLET,
        ),
        LocalTuyaEntity(
            translation_key="switch_6",
            id=DPCode.SWITCH_6,
            name="Switch 6",
            device_class=SwitchDeviceClass.OUTLET,
        ),
        LocalTuyaEntity(
            translation_key="usb_1",
            id=DPCode.SWITCH_USB1,
            name="USB 1",
        ),
        LocalTuyaEntity(
            translation_key="usb_2",
            id=DPCode.SWITCH_USB2,
            name="USB 2",
        ),
        LocalTuyaEntity(
            translation_key="usb_3",
            id=DPCode.SWITCH_USB3,
            name="USB 3",
        ),
        LocalTuyaEntity(
            translation_key="usb_4",
            id=DPCode.SWITCH_USB4,
            name="USB 4",
        ),
        LocalTuyaEntity(
            translation_key="usb_5",
            id=DPCode.SWITCH_USB5,
            name="USB 5",
        ),
        LocalTuyaEntity(
            translation_key="usb_6",
            id=DPCode.SWITCH_USB6,
            name="USB 6",
        ),
        LocalTuyaEntity(
            translation_key="socket",
            id=DPCode.SWITCH,
            name="Socket",
            device_class=SwitchDeviceClass.OUTLET,
        ),
    ),
    # Smart panel with switches and zigbee hub ?
    # Not documented
    DeviceCategory.DGNZK: (
        LocalTuyaEntity(
            translation_key="switch",
            id=DPCode.SWITCH,
            name="Switch",
        ),
        LocalTuyaEntity(
            translation_key="switch_1",
            id=(DPCode.SWITCH_1, DPCode.SWITCH1),
            name="Switch 1",
        ),
        LocalTuyaEntity(
            translation_key="switch_2",
            id=(DPCode.SWITCH_2, DPCode.SWITCH2),
            name="Switch 2",
        ),
        LocalTuyaEntity(
            translation_key="switch_3",
            id=(DPCode.SWITCH_3, DPCode.SWITCH3),
            name="Switch 3",
        ),
        LocalTuyaEntity(
            translation_key="switch_4",
            id=(DPCode.SWITCH_4, DPCode.SWITCH4),
            name="Switch 4",
        ),
        LocalTuyaEntity(
            translation_key="switch_5",
            id=(DPCode.SWITCH_5, DPCode.SWITCH5),
            name="Switch 5",
        ),
        LocalTuyaEntity(
            translation_key="switch_6",
            id=(DPCode.SWITCH_6, DPCode.SWITCH6),
            name="Switch 6",
        ),
        LocalTuyaEntity(
            translation_key="voice",
            id=DPCode.VOICE_PLAY,
            name="Voice",
            icon="mdi:play",
        ),
        LocalTuyaEntity(
            translation_key="bt_voice",
            id=DPCode.VOICE_BT_PLAY,
            name="BT Voice",
            icon="mdi:play",
        ),
        LocalTuyaEntity(
            translation_key="mute",
            id=DPCode.MUTE,
            name="Mute",
            icon="mdi:volume-off",
        ),
        LocalTuyaEntity(
            translation_key="microphone",
            id=DPCode.VOICE_MIC,
            name="Microphone",
            icon="mdi:microphone-off",
        ),
        LocalTuyaEntity(
            translation_key="welcome",
            id=DPCode.SWITCH_WELCOME,
            name="Welcome",
            icon="mdi:human-greeting",
        ),
    ),
    # EV Charcher
    # https://developer.tuya.com/en/docs/iot/categoryqn?id=Kaiuz18kih0sm
    DeviceCategory.QCCDZ: (
        LocalTuyaEntity(
            translation_key="switch",
            id=DPCode.SWITCH,
        ),
    ),
    DeviceCategory.GCJ: (
        LocalTuyaEntity(
            translation_key="rain_mode",
            id=DPCode.MACHINERAINMODE,
            name="Rain Mode",
            icon="mdi:weather-rainy",
        ),
    ),
    # Unknown product with switch capabilities
    # Fond in some diffusers, plugs and PIR flood lights
    # Not documented
    DeviceCategory.QJDCZ: (
        LocalTuyaEntity(
            translation_key="switch",
            id=DPCode.SWITCH_1,
            name="Switch",
        ),
    ),
    # Heater
    # https://developer.tuya.com/en/docs/iot/categoryqn?id=Kaiuz18kih0sm
    DeviceCategory.QN: (
        LocalTuyaEntity(
            translation_key="ionizer",
            id=DPCode.ANION,
            name="Ionizer",
            icon="mdi:minus-circle-outline",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="child_lock",
            id=DPCode.LOCK,
            name="Child Lock",
            icon="mdi:account-lock",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Weather Station
    DeviceCategory.QXJ: (
        LocalTuyaEntity(
            translation_key="switch",
            id=DPCode.SWITCH,
            name="Switch",
            device_class=SwitchDeviceClass.OUTLET,
        ),
    ),
    # Electric desk
    # Undocumented
    DeviceCategory.SJZ: (
        LocalTuyaEntity(
            translation_key="child_lock",
            id=DPCode.CHILD_LOCK,
            name="Child Lock",
            icon="mdi:account-lock",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Smart indoor garden
    # https://developer.tuya.com/en/docs/iot/categorysz?id=Kaiuz4e6h7up0
    DeviceCategory.SZ: (
        LocalTuyaEntity(
            translation_key="power",
            id=DPCode.SWITCH,
            name="Power",
        ),
        LocalTuyaEntity(
            translation_key="pump",
            id=DPCode.PUMP,
            name="Pump",
        ),
    ),
    # Gateway control
    # https://developer.tuya.com/en/docs/iot/wg?id=Kbcdadk79ejok
    DeviceCategory.WG2: (
        LocalTuyaEntity(
            translation_key="mute",
            id=DPCode.MUFFLING,
            name="Mute",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Micro Storage Inverter
    DeviceCategory.XNYJCN: (
        LocalTuyaEntity(
            translation_key="output_power_limit",
            id=DPCode.FEEDIN_POWER_LIMIT_ENABLE,
            name="Output Power Limit",
            icon="mdi:transmission-tower",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Smoke Alarm
    # https://developer.tuya.com/en/docs/iot/categoryywbj?id=Kaiuz3f6sf952
    DeviceCategory.YWBJ: (
        LocalTuyaEntity(
            translation_key="mute",
            id=DPCode.MUFFLING,
            name="Mute",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Hejhome whitelabel Fingerbot
    # Undocumented
    DeviceCategory.ZNJXS: (
        LocalTuyaEntity(
            translation_key="switch",
            id=DPCode.SWITCH,
            name="Switch",
        ),
    ),
    # Pool HeatPump
    # Undocumented
    DeviceCategory.ZNRB: (
        LocalTuyaEntity(
            translation_key="child_lock",
            id=DPCode.CHILD_LOCK,
            name="Child Lock",
            icon="mdi:account-lock",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="switch",
            id=DPCode.SWITCH,
            name="Switch",
        ),
    ),
    # Generic products, EV Charger
    # https://support.tuya.com/en/help/_detail/K9g77zfmlnwal
    DeviceCategory.QT: (
        LocalTuyaEntity(
            translation_key="charge",
            id=DPCode.CHARGING_STATE,
            icon="mdi:ev-plug-tesla",
            name="Charge",
        ),
    ),
    # Robot Vacuum
    # https://developer.tuya.com/en/docs/iot/fsd?id=K9gf487ck1tlo
    DeviceCategory.SD: (
        LocalTuyaEntity(
            translation_key="do_not_disturb",
            id=DPCode.SWITCH_DISTURB,
            name="Do Not Disturb",
            icon="mdi:minus-circle",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="mute_voice",
            id=DPCode.VOICE_SWITCH,
            name="Mute Voice",
            icon="mdi:account-voice",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="map_resetting",
            id=DPCode.RESET_MAP,
            name="Map Resetting",
            icon="mdi:backup-restore",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="resumable_cleaning",
            id=DPCode.BREAK_CLEAN,
            name="Resumable Cleaning",
            icon="mdi:cog-play-outline",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="mop_y",
            id=DPCode.Y_MOP,
            name="Mop Y",
            icon="mdi:dots-vertical",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Water Valve
    DeviceCategory.SFKZQ: (
        LocalTuyaEntity(
            translation_key="switch",
            id=DPCode.SWITCH,
            icon="mdi:valve",
        ),
        LocalTuyaEntity(
            translation_key="smart_weather",
            id=DPCode.SWITCH_WEATHER,
            name="Smart Weather",
            icon="mdi:auto-mode",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Siren Alarm
    # https://developer.tuya.com/en/docs/iot/categorysgbj?id=Kaiuz37tlpbnu
    DeviceCategory.SGBJ: (
        LocalTuyaEntity(
            translation_key="mute",
            id=DPCode.MUFFLING,
            name="Mute",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Smart Camera
    # https://developer.tuya.com/en/docs/iot/categorysp?id=Kaiuz35leyo12
    DeviceCategory.SP: (
        LocalTuyaEntity(
            translation_key="battery_lock",
            id=DPCode.WIRELESS_BATTERYLOCK,
            name="Battery Lock",
            icon="mdi:battery-lock",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="cry_detection",
            id=DPCode.CRY_DETECTION_SWITCH,
            name="Cry Detection",
            icon="mdi:emoticon-cry",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="sound_detection",
            id=DPCode.DECIBEL_SWITCH,
            name="Sound Detection",
            icon="mdi:microphone-outline",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="video_recording",
            id=DPCode.RECORD_SWITCH,
            name="Video Recording",
            icon="mdi:record-rec",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="motion_recording",
            id=DPCode.MOTION_RECORD,
            name="Motion Recording",
            icon="mdi:record-rec",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="privacy_mode",
            id=DPCode.BASIC_PRIVATE,
            name="Privacy Mode",
            icon="mdi:eye-off",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="flip",
            id=DPCode.BASIC_FLIP,
            name="Flip",
            icon="mdi:flip-horizontal",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="time_watermark",
            id=DPCode.BASIC_OSD,
            name="Time Watermark",
            icon="mdi:watermark",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="wide_dynamic_range",
            id=DPCode.BASIC_WDR,
            name="Wide Dynamic Range",
            icon="mdi:watermark",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="motion_tracking",
            id=DPCode.MOTION_TRACKING,
            name="Motion Tracking",
            icon="mdi:motion-sensor",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="motion_alarm",
            id=DPCode.MOTION_SWITCH,
            name="Motion Alarm",
            icon="mdi:motion-sensor",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="use_motion_detection_zone",
            id=DPCode.MOTION_AREA_SWITCH,
            name="Use Motion Detection Zone",
            icon="mdi:selection-multiple",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="auto_trigger_siren",
            id=DPCode.IPC_AUTO_SIREN,
            name="Auto-trigger Siren",
            icon="mdi:alarm-light-outline",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="ptz_stop",
            id=DPCode.PTZ_STOP,
            name="PTZ Stop",
            icon="mdi:stop-circle",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Fingerbot
    DeviceCategory.SZJQR: (
        LocalTuyaEntity(
            translation_key="switch",
            id=DPCode.SWITCH,
            name="Switch",
            icon="mdi:cursor-pointer",
        ),
    ),
    # IoT Switch?
    # Note: Undocumented
    DeviceCategory.TDQ: (
        LocalTuyaEntity(
            translation_key="switch_1",
            id=DPCode.SWITCH_1,
            name="Switch 1",
            device_class=SwitchDeviceClass.OUTLET,
        ),
        LocalTuyaEntity(
            translation_key="switch_2",
            id=DPCode.SWITCH_2,
            name="Switch 2",
            device_class=SwitchDeviceClass.OUTLET,
        ),
        LocalTuyaEntity(
            translation_key="switch_3",
            id=DPCode.SWITCH_3,
            name="Switch 3",
            device_class=SwitchDeviceClass.OUTLET,
        ),
        LocalTuyaEntity(
            translation_key="switch_4",
            id=DPCode.SWITCH_4,
            name="Switch 4",
            device_class=SwitchDeviceClass.OUTLET,
        ),
        LocalTuyaEntity(
            translation_key="switch_5",
            id=DPCode.SWITCH_5,
            name="Switch 5",
            device_class=SwitchDeviceClass.OUTLET,
        ),
        LocalTuyaEntity(
            translation_key="switch_6",
            id=DPCode.SWITCH_6,
            name="Switch 6",
            device_class=SwitchDeviceClass.OUTLET,
        ),
        LocalTuyaEntity(
            translation_key="child_lock",
            id=DPCode.CHILD_LOCK,
            name="Child Lock",
            icon="mdi:account-lock",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Solar Light
    # https://developer.tuya.com/en/docs/iot/tynd?id=Kaof8j02e1t98
    DeviceCategory.TYNDJ: (
        LocalTuyaEntity(
            translation_key="energy_saving",
            id=DPCode.SWITCH_SAVE_ENERGY,
            name="Energy Saving",
            icon="mdi:leaf",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # PIR Detector
    # https://developer.tuya.com/en/docs/iot/categorypir?id=Kaiuz3ss11b80
    DeviceCategory.PIR: (
        LocalTuyaEntity(
            translation_key="timer",
            id=DPCode.MOD_ON_TMR,
            icon="mdi:timer-play",
            entity_category=EntityCategory.CONFIG,
            name="Timer",
        ),
    ),
    # Thermostatic Radiator Valve
    # Not documented
    DeviceCategory.WKF: (
        LocalTuyaEntity(
            translation_key="child_lock",
            id=DPCode.CHILD_LOCK,
            name="Child Lock",
            icon="mdi:account-lock",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="open_window_detection",
            id=(DPCode.WINDOW_CHECK, DPCode.WINDOW_STATE),
            name="Open Window Detection",
            icon="mdi:window-open",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Air Conditioner Mate (Smart IR Socket)
    DeviceCategory.WNYKQ: (
        LocalTuyaEntity(
            translation_key="switch",
            id=DPCode.SWITCH,
            name="Switch",
        ),
    ),
    # Zigbee Gateway (dunno if it's useful)
    # "wg2": (
    #     LocalTuyaEntity(
    #         id=DPCode.SWITCH_ALARM_SOUND,
    #         name="Switch",
    #     ),
    # ),
    # SIREN: Siren (switch) with Temperature and humidity sensor
    # https://developer.tuya.com/en/docs/iot/f?id=Kavck4sr3o5ek
    DeviceCategory.WSDCG: (
        LocalTuyaEntity(
            translation_key="switch",
            id=DPCode.SWITCH,
            name="Switch",
            device_class=SwitchDeviceClass.OUTLET,
        ),
    ),
    # Ceiling Light
    # https://developer.tuya.com/en/docs/iot/ceiling-light?id=Kaiuz03xxfc4r
    DeviceCategory.XDD: (
        LocalTuyaEntity(
            translation_key="do_not_disturb",
            id=DPCode.DO_NOT_DISTURB,
            name="Do Not Disturb",
            icon="mdi:minus-circle-outline",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Diffuser
    # https://developer.tuya.com/en/docs/iot/categoryxxj?id=Kaiuz1f9mo6bl
    DeviceCategory.XXJ: (
        LocalTuyaEntity(
            translation_key="power",
            id=DPCode.SWITCH,
            name="Power",
        ),
        LocalTuyaEntity(
            translation_key="spray",
            id=DPCode.SWITCH_SPRAY,
            name="Spray",
            icon="mdi:spray",
        ),
        LocalTuyaEntity(
            translation_key="voice",
            id=DPCode.SWITCH_VOICE,
            name="Voice",
            icon="mdi:account-voice",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Smart Electricity Meter
    # https://developer.tuya.com/en/docs/iot/smart-meter?id=Kaiuz4gv6ack7
    DeviceCategory.ZNDB: (
        LocalTuyaEntity(
            translation_key="switch",
            id=DPCode.SWITCH,
            name="Switch",
        ),
    ),
    # Fan
    # https://developer.tuya.com/en/docs/iot/categoryfs?id=Kaiuz1xweel1c
    DeviceCategory.FS: (
        LocalTuyaEntity(
            translation_key="anion",
            id=DPCode.ANION,
            name="Anion",
            icon="mdi:atom",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="humidification",
            id=DPCode.HUMIDIFIER,
            name="Humidification",
            icon="mdi:air-humidifier",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="oxygen_bar",
            id=DPCode.OXYGEN,
            name="Oxygen Bar",
            icon="mdi:molecule",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="natural_wind",
            id=DPCode.FAN_COOL,
            name="Natural Wind",
            icon="mdi:weather-windy",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="sound",
            id=DPCode.FAN_BEEP,
            name="Sound",
            icon="mdi:minus-circle",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="child_lock",
            id=DPCode.CHILD_LOCK,
            name="Child Lock",
            icon="mdi:account-lock",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="lcd",
            id=DPCode.LCD_ONOF,
            name="LCD",
            icon="mdi:television",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="sound",
            id=DPCode.SPEEK,
            name="Sound",
            icon="mdi:volume-medium",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Fan switch
    DeviceCategory.FSKG: (
        LocalTuyaEntity(
            translation_key="led_switch",
            id=DPCode.BACKLIGHT_SWITCH,
            name="LED Switch",
            icon="mdi:led-outline",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Curtain
    # https://developer.tuya.com/en/docs/iot/f?id=K9gf46o5mtfyc
    DeviceCategory.CL: (
        LocalTuyaEntity(
            translation_key="reverse",
            id=DPCode.CONTROL_BACK,
            name="Reverse",
            icon="mdi:swap-horizontal",
            entity_category=EntityCategory.CONFIG,
            condition_contains_any=["true", "false"],
        ),
        LocalTuyaEntity(
            translation_key="reverse",
            id=DPCode.OPPOSITE,
            name="Reverse",
            icon="mdi:swap-horizontal",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="set_upper_limit",
            id=DPCode.UP_CONFIRM,
            name="Set Upper Limit",
            icon="mdi:arrow-collapse-up",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="set_middle_limit",
            id=DPCode.MIDDLE_CONFIRM,
            name="Set Middle Limit",
            icon="mdi:format-vertical-align-center",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="set_down_limit",
            id=DPCode.DOWN_CONFIRM,
            name="Set Down Limit",
            icon="mdi:arrow-collapse-down",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Humidifier
    # https://developer.tuya.com/en/docs/iot/categoryjsq?id=Kaiuz1smr440b
    DeviceCategory.JSQ: (
        LocalTuyaEntity(
            translation_key="voice",
            id=DPCode.SWITCH_SOUND,
            name="Voice",
            icon="mdi:account-voice",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="sleep",
            id=DPCode.SLEEP,
            name="Sleep",
            icon="mdi:power-sleep",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="sterilization",
            id=DPCode.STERILIZATION,
            name="Sterilization",
            icon="mdi:minus-circle-outline",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="spray",
            id=DPCode.SWITCH_SPRAY,
            name="Spray",
            icon="mdi:spray",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Alarm Host
    # https://developer.tuya.com/en/docs/iot/categorymal?id=Kaiuz33clqxaf
    DeviceCategory.MAL: (
        LocalTuyaEntity(
            translation_key="sound",
            id=DPCode.SWITCH_ALARM_SOUND,
            name="Sound",
            icon="mdi:volume-source",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="light",
            id=DPCode.SWITCH_ALARM_LIGHT,
            name="Light",
            icon="mdi:alarm-light-outline",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="key_tone_sound",
            id=DPCode.SWITCH_KB_SOUND,
            name="Key Tone Sound",
            icon="mdi:volume-source",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="keypad_light",
            id=DPCode.SWITCH_KB_LIGHT,
            name="Keypad Light",
            icon="mdi:alarm-light-outline",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="call",
            id=DPCode.SWITCH_ALARM_CALL,
            name="Call",
            icon="mdi:phone",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="sms",
            id=DPCode.SWITCH_ALARM_SMS,
            name="SMS",
            icon="mdi:message",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="push_notification",
            id=DPCode.SWITCH_ALARM_PROPEL,
            name="Push Notification",
            icon="mdi:bell-badge-outline",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="mute",
            id=DPCode.MUFFLING,
            name="Mute",
            icon="mdi:volume-mute",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Smart Water Meter
    # https://developer.tuya.com/en/docs/iot/f?id=Ka8n052xu7w4c
    DeviceCategory.ZNSB: (
        LocalTuyaEntity(
            translation_key="valve",
            id=DPCode.SWITCH_COLD,
            name="Valve",
            icon="mdi:Valve",
        ),
        LocalTuyaEntity(
            translation_key="auto_clean",
            id=DPCode.AUTO_CLEAN,
            name="Auto Clean",
            icon="mdi:auto-fix",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Thermostat
    # https://developer.tuya.com/en/docs/iot/f?id=K9gf45ld5l0t9
    DeviceCategory.WK: (
        LocalTuyaEntity(
            translation_key="child_lock",
            id=DPCode.CHILD_LOCK,
            name="Child Lock",
            icon="mdi:account-lock",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="frost_protection",
            id=DPCode.FROST,
            name="Frost Protection",
            icon="mdi:snowflake-alert",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            translation_key="eco",
            id=DPCode.ECO,
            name="ECO",
            icon="mdi:sprout",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Ceiling fan light
    # https://developer.tuya.com/en/docs/iot/fsd?id=Kaof8eiei4c2v
    DeviceCategory.FSD: (
        LocalTuyaEntity(
            translation_key="sound",
            id=DPCode.FAN_BEEP,
            name="Sound",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Irrigator
    # https://developer.tuya.com/en/docs/iot/categoryggq?id=Kaiuz1qib7z0k
    DeviceCategory.GGQ: (
        LocalTuyaEntity(
            translation_key="switch_1",
            id=DPCode.SWITCH_1,
            name="Switch 1",
        ),
        LocalTuyaEntity(
            translation_key="switch_2",
            id=DPCode.SWITCH_2,
            name="Switch 2",
        ),
        LocalTuyaEntity(
            translation_key="switch_3",
            id=DPCode.SWITCH_3,
            name="Switch 3",
        ),
        LocalTuyaEntity(
            translation_key="switch_4",
            id=DPCode.SWITCH_4,
            name="Switch 4",
        ),
        LocalTuyaEntity(
            translation_key="switch_5",
            id=DPCode.SWITCH_5,
            name="Switch 5",
        ),
        LocalTuyaEntity(
            translation_key="switch_6",
            id=DPCode.SWITCH_6,
            name="Switch 6",
        ),
        LocalTuyaEntity(
            translation_key="switch_7",
            id=DPCode.SWITCH_7,
            name="Switch 7",
        ),
        LocalTuyaEntity(
            translation_key="switch_8",
            id=DPCode.SWITCH_8,
            name="Switch 8",
        ),
    ),
    # Tower fan
    DeviceCategory.KS: (
        LocalTuyaEntity(
            translation_key="ionizer",
            id=DPCode.ANION,
            name="Ionizer",
            icon="mdi:minus-circle-outline",
        ),
    ),
}

# Scene Switch
# https://developer.tuya.com/en/docs/iot/f?id=K9gf7nx6jelo8
SWITCHES[DeviceCategory.CJKG] = SWITCHES[DeviceCategory.KG]

# Wireless Switch
SWITCHES[DeviceCategory.WXKG] = SWITCHES[DeviceCategory.KG]

# Socket (duplicate of `pc`)
SWITCHES[DeviceCategory.CZ] = SWITCHES[DeviceCategory.PC]

# Dehumidifier
# https://developer.tuya.com/en/docs/iot/categorycs?id=Kaiuz1vcz4dha
SWITCHES[DeviceCategory.CS] = SWITCHES[DeviceCategory.JSQ]
