"""
    This a file contains available tuya data
    https://developer.tuya.com/en/docs/iot/standarddescription?id=K9i5ql6waswzq

    Credits: official HA Tuya integration.
    Modified by: xZetsubou
"""

from .base import (
    DeviceCategory,
    DPCode,
    LocalTuyaEntity,
    CONF_DEVICE_CLASS,
    EntityCategory,
    CLOUD_VALUE,
)

# from const.py this is temporarily.

from ...select import CONF_OPTIONS as OPS_VALS


def localtuya_selector(options):
    """Generate localtuya select configs"""
    data = {OPS_VALS: CLOUD_VALUE(options, "id", "range", dict)}
    return data


COUNT_DOWN = {
    "cancel": "Disable",
    "1": "1 Hour",
    "2": "2 Hours",
    "3": "3 Hours",
    "4": "4 Hours",
    "5": "5 Hours",
    "6": "6 Hours",
}
COUNT_DOWN_HOURS = {
    "off": "Disable",
    "1h": "1 Hour",
    "2h": "2 Hours",
    "3h": "3 Hours",
    "4h": "4 Hours",
    "5h": "5 Hours",
    "6h": "6 Hours",
}

SELECTS: dict[DeviceCategory, tuple[LocalTuyaEntity, ...]] = {
    # Smart Kettle
    DeviceCategory.BH: (
        LocalTuyaEntity(
            translation_key="quick_heat_temperature",
            id=DPCode.TEMP_SETTING_QUICK_C,
            entity_category=EntityCategory.CONFIG,
            name="Quick Heat Temperature",
            custom_configs=localtuya_selector(
                {
                    "light_boil": "Light",
                    "moderate_boil": "Moderate",
                    "strong_boil": "Strong",
                }
            ),
        ),
        LocalTuyaEntity(
            translation_key="kettle_work_mode",
            id=DPCode.WORK_TYPE,
            entity_category=EntityCategory.CONFIG,
            name="Kettle Work Mode",
            custom_configs=localtuya_selector(
                {"heating": "Heating", "keep_warm": "Keep Warm"}
            ),
        ),
    ),
    # Smart panel with switches and zigbee hub ?
    # Not documented
    DeviceCategory.DGNZK: (
        LocalTuyaEntity(
            translation_key="source",
            id=DPCode.SOURCE,
            name="Source",
            icon="mdi:volume-source",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_selector(
                {
                    "cloud": "Cloud",
                    "local": "Local",
                    "aux": "Aux",
                    "bluetooth": "Bluetooth",
                }
            ),
        ),
        LocalTuyaEntity(
            translation_key="mode",
            id=DPCode.PLAY_MODE,
            name="Mode",
            icon="mdi:cog-outline",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_selector(
                {
                    "order": "Order",
                    "repeat_all": "Repeat ALL",
                    "repeat_one": "Repeat one",
                    "random": "Random",
                }
            ),
        ),
        LocalTuyaEntity(
            translation_key="sound_effects",
            id=DPCode.SOUND_EFFECTS,
            name="Sound Effects",
            icon="mdi:sine-wave",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_selector(
                {
                    "normal": "Normal",
                    "pop": "Pop",
                    "opera": "Opera",
                    "classical": "Classical",
                    "jazz": "Jazz",
                    "rock": "Rock",
                    "folk": "Folk",
                    "heavy_metal": "Metal",
                    "hip_hop": "HipHop",
                    "wave": "Wave",
                }
            ),
        ),
    ),
    # Multi-functional Sensor
    # https://developer.tuya.com/en/docs/iot/categorydgnbj?id=Kaiuz3yorvzg3
    DeviceCategory.DGNBJ: (
        LocalTuyaEntity(
            translation_key="volume",
            id=DPCode.ALARM_VOLUME,
            name="volume",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_selector(
                {
                    "low": "Low",
                    "middle": "Middle",
                    "high": "High",
                    "mute": "Mute",
                }
            ),
        ),
        LocalTuyaEntity(
            translation_key="ringtone",
            id=DPCode.ALARM_RINGTONE,
            name="Ringtone",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_selector(
                {
                    "1": "1",
                    "2": "2",
                    "3": "3",
                    "4": "4",
                    "5": "5",
                }
            ),
        ),
    ),
    # CO2 Detector
    DeviceCategory.CO2BJ: (
        LocalTuyaEntity(
            translation_key="volume",
            id=DPCode.ALARM_VOLUME,
            name="Volume",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_selector(
                {"low": "Low", "middle": "Middle", "high": "High", "mute": "Mute"}
            ),
        ),
    ),
    # Smart Odor Eliminator-Pro
    DeviceCategory.CWJWQ: (
        LocalTuyaEntity(
            translation_key="odor_elimination_mode",
            id=DPCode.WORK_MODE,
            entity_category=EntityCategory.CONFIG,
            name="Odor Elimination Mode",
            custom_configs=localtuya_selector(
                {"deodorization": "Deodorization", "sterilization": "Sterilization"}
            ),
        ),
    ),
    # Heater
    DeviceCategory.KT: (
        LocalTuyaEntity(
            translation_key="temperature_unit",
            id=(DPCode.C_F, DPCode.TEMP_UNIT_CONVERT),
            name="Temperature Unit",
            custom_configs=localtuya_selector({"c": "Celsius", "f": "Fahrenheit"}),
        ),
    ),
    # Heater
    DeviceCategory.RS: (
        LocalTuyaEntity(
            translation_key="temperature_unit",
            id=(DPCode.C_F, DPCode.TEMP_UNIT_CONVERT),
            name="Temperature Unit",
            custom_configs=localtuya_selector({"c": "Celsius", "f": "Fahrenheit"}),
        ),
        LocalTuyaEntity(
            translation_key="cruise_mode",
            id=DPCode.CRUISE_MODE,
            name="Cruise mode",
            custom_configs=localtuya_selector(
                {"all_day": "Always", "water_control": "Water", "single_cruise": "Once"}
            ),
        ),
    ),
    # Coffee maker
    # https://developer.tuya.com/en/docs/iot/categorykfj?id=Kaiuz2p12pc7f
    DeviceCategory.KFJ: (
        LocalTuyaEntity(
            translation_key="cups",
            id=DPCode.CUP_NUMBER,
            name="Cups",
            icon="mdi:numeric",
            custom_configs=localtuya_selector(
                {
                    "1": "1",
                    "2": "2",
                    "3": "3",
                    "4": "4",
                    "5": "5",
                    "6": "6",
                    "7": "7",
                    "8": "8",
                    "9": "9",
                    "10": "10",
                    "11": "11",
                    "12": "12",
                }
            ),
        ),
        LocalTuyaEntity(
            translation_key="concentration",
            id=DPCode.CONCENTRATION_SET,
            name="Concentration",
            icon="mdi:altimeter",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_selector(
                {"regular": "REGULAR", "middle": "MIDDLE", "bold": "BOLD"}
            ),
        ),
        LocalTuyaEntity(
            translation_key="material",
            id=DPCode.MATERIAL,
            name="Material",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_selector({"bean": "BEAN", "powder": "POWDER"}),
        ),
        LocalTuyaEntity(
            translation_key="mode",
            id=DPCode.MODE,
            name="Mode",
            icon="mdi:coffee",
            custom_configs=localtuya_selector(
                {
                    "espresso": "Espresso",
                    "americano": "Americano",
                    "machiatto": "Machiatto",
                    "caffe_latte": "Latte",
                    "caffe_mocha": "Mocha",
                    "cappuccino": "Cappuccino",
                }
            ),
        ),
    ),
    # Switch
    # https://developer.tuya.com/en/docs/iot/s?id=K9gf7o5prgf7s
    DeviceCategory.KG: (
        LocalTuyaEntity(
            translation_key="power_on_behavior",
            id=DPCode.RELAY_STATUS,
            icon="mdi:circle-double",
            entity_category=EntityCategory.CONFIG,
            name="Power-on behavior",
            custom_configs=localtuya_selector(
                {"power_on": "ON", "power_off": "OFF", "last": "Last State"}
            ),
            condition_contains_any=["power_on", "power_off", "last"],
        ),
        LocalTuyaEntity(
            translation_key="power_on_behavior",
            id=DPCode.RELAY_STATUS,
            icon="mdi:circle-double",
            entity_category=EntityCategory.CONFIG,
            name="Power-on behavior",
            custom_configs=localtuya_selector(
                {"on": "ON", "off": "OFF", "memory": "Last State"}
            ),
            condition_contains_any=["on", "off", "memory"],
        ),
        LocalTuyaEntity(
            translation_key="power_on_behavior",
            id=DPCode.RELAY_STATUS,
            icon="mdi:circle-double",
            entity_category=EntityCategory.CONFIG,
            name="Power-on behavior",
            custom_configs=localtuya_selector(
                {"0": "ON", "1": "OFF", "2": "Last State"}
            ),
        ),
        LocalTuyaEntity(
            translation_key="power_on_behavior_1",
            id=DPCode.RELAY_STATUS_1,
            icon="mdi:circle-double",
            entity_category=EntityCategory.CONFIG,
            name="Power-on behavior 1",
            custom_configs=localtuya_selector(
                {"power_on": "ON", "power_off": "OFF", "last": "Last State"}
            ),
            condition_contains_any=["power_on", "power_off", "last"],
        ),
        LocalTuyaEntity(
            translation_key="power_on_behavior_1",
            id=DPCode.RELAY_STATUS_1,
            icon="mdi:circle-double",
            entity_category=EntityCategory.CONFIG,
            name="Power-on behavior 1",
            custom_configs=localtuya_selector(
                {"on": "ON", "off": "OFF", "memory": "Last State"}
            ),
            condition_contains_any=["on", "off", "memory"],
        ),
        LocalTuyaEntity(
            translation_key="power_on_behavior_1",
            id=DPCode.RELAY_STATUS_1,
            icon="mdi:circle-double",
            entity_category=EntityCategory.CONFIG,
            name="Power-on behavior 1",
            custom_configs=localtuya_selector(
                {"0": "ON", "1": "OFF", "2": "Last State"}
            ),
        ),
        LocalTuyaEntity(
            translation_key="power_on_behavior_2",
            id=DPCode.RELAY_STATUS_2,
            icon="mdi:circle-double",
            entity_category=EntityCategory.CONFIG,
            name="Power-on behavior 2",
            custom_configs=localtuya_selector(
                {"power_on": "ON", "power_off": "OFF", "last": "Last State"}
            ),
            condition_contains_any=["power_on", "power_off", "last"],
        ),
        LocalTuyaEntity(
            translation_key="power_on_behavior_2",
            id=DPCode.RELAY_STATUS_2,
            icon="mdi:circle-double",
            entity_category=EntityCategory.CONFIG,
            name="Power-on behavior 2",
            custom_configs=localtuya_selector(
                {"on": "ON", "off": "OFF", "memory": "Last State"}
            ),
            condition_contains_any=["on", "off", "memory"],
        ),
        LocalTuyaEntity(
            translation_key="power_on_behavior_2",
            id=DPCode.RELAY_STATUS_2,
            icon="mdi:circle-double",
            entity_category=EntityCategory.CONFIG,
            name="Power-on behavior 2",
            custom_configs=localtuya_selector(
                {"0": "ON", "1": "OFF", "2": "Last State"}
            ),
        ),
        LocalTuyaEntity(
            translation_key="power_on_behavior_3",
            id=DPCode.RELAY_STATUS_3,
            icon="mdi:circle-double",
            entity_category=EntityCategory.CONFIG,
            name="Power-on behavior 3",
            custom_configs=localtuya_selector(
                {"power_on": "ON", "power_off": "OFF", "last": "Last State"}
            ),
            condition_contains_any=["power_on", "power_off", "last"],
        ),
        LocalTuyaEntity(
            translation_key="power_on_behavior_3",
            id=DPCode.RELAY_STATUS_3,
            icon="mdi:circle-double",
            entity_category=EntityCategory.CONFIG,
            name="Power-on behavior 3",
            custom_configs=localtuya_selector(
                {"on": "ON", "off": "OFF", "memory": "Last State"}
            ),
            condition_contains_any=["on", "off", "memory"],
        ),
        LocalTuyaEntity(
            translation_key="power_on_behavior_3",
            id=DPCode.RELAY_STATUS_3,
            icon="mdi:circle-double",
            entity_category=EntityCategory.CONFIG,
            name="Power-on behavior 3",
            custom_configs=localtuya_selector(
                {"0": "ON", "1": "OFF", "2": "Last State"}
            ),
        ),
        LocalTuyaEntity(
            translation_key="power_on_behavior_4",
            id=DPCode.RELAY_STATUS_4,
            icon="mdi:circle-double",
            entity_category=EntityCategory.CONFIG,
            name="Power-on behavior 4",
            custom_configs=localtuya_selector(
                {"power_on": "ON", "power_off": "OFF", "last": "Last State"}
            ),
            condition_contains_any=["power_on", "power_off", "last"],
        ),
        LocalTuyaEntity(
            translation_key="power_on_behavior_4",
            id=DPCode.RELAY_STATUS_4,
            icon="mdi:circle-double",
            entity_category=EntityCategory.CONFIG,
            name="Power-on behavior 4",
            custom_configs=localtuya_selector(
                {"on": "ON", "off": "OFF", "memory": "Last State"}
            ),
            condition_contains_any=["on", "off", "memory"],
        ),
        LocalTuyaEntity(
            translation_key="power_on_behavior_4",
            id=DPCode.RELAY_STATUS_4,
            icon="mdi:circle-double",
            entity_category=EntityCategory.CONFIG,
            name="Power-on behavior 4",
            custom_configs=localtuya_selector(
                {"0": "ON", "1": "OFF", "2": "Last State"}
            ),
        ),
        LocalTuyaEntity(
            translation_key="power_on_behavior_5",
            id=DPCode.RELAY_STATUS_5,
            icon="mdi:circle-double",
            entity_category=EntityCategory.CONFIG,
            name="Power-on behavior 5",
            custom_configs=localtuya_selector(
                {"power_on": "ON", "power_off": "OFF", "last": "Last State"}
            ),
            condition_contains_any=["power_on", "power_off", "last"],
        ),
        LocalTuyaEntity(
            translation_key="power_on_behavior_5",
            id=DPCode.RELAY_STATUS_5,
            icon="mdi:circle-double",
            entity_category=EntityCategory.CONFIG,
            name="Power-on behavior 5",
            custom_configs=localtuya_selector(
                {"on": "ON", "off": "OFF", "memory": "Last State"}
            ),
            condition_contains_any=["on", "off", "memory"],
        ),
        LocalTuyaEntity(
            translation_key="power_on_behavior_5",
            id=DPCode.RELAY_STATUS_5,
            icon="mdi:circle-double",
            entity_category=EntityCategory.CONFIG,
            name="Power-on behavior 5",
            custom_configs=localtuya_selector(
                {"0": "ON", "1": "OFF", "2": "Last State"}
            ),
        ),
        LocalTuyaEntity(
            translation_key="power_on_behavior_6",
            id=DPCode.RELAY_STATUS_6,
            icon="mdi:circle-double",
            entity_category=EntityCategory.CONFIG,
            name="Power-on behavior 6",
            custom_configs=localtuya_selector(
                {"power_on": "ON", "power_off": "OFF", "last": "Last State"}
            ),
            condition_contains_any=["power_on", "power_off", "last"],
        ),
        LocalTuyaEntity(
            translation_key="power_on_behavior_6",
            id=DPCode.RELAY_STATUS_6,
            icon="mdi:circle-double",
            entity_category=EntityCategory.CONFIG,
            name="Power-on behavior 6",
            custom_configs=localtuya_selector(
                {"on": "ON", "off": "OFF", "memory": "Last State"}
            ),
            condition_contains_any=["on", "off", "memory"],
        ),
        LocalTuyaEntity(
            translation_key="power_on_behavior_6",
            id=DPCode.RELAY_STATUS_6,
            icon="mdi:circle-double",
            entity_category=EntityCategory.CONFIG,
            name="Power-on behavior 6",
            custom_configs=localtuya_selector(
                {"0": "ON", "1": "OFF", "2": "Last State"}
            ),
        ),
        LocalTuyaEntity(
            translation_key="light_mode",
            id=DPCode.LIGHT_MODE,
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_selector(
                {"relay": "State", "pos": "Position", "none": "OFF"}
            ),
            name="Light Mode",
        ),
    ),
    # Cat litter box
    # https://developer.tuya.com/en/docs/iot/f?id=Kakg309qkmuit
    DeviceCategory.MSP: (
        LocalTuyaEntity(
            translation_key="doorbell_song",
            id=DPCode.LEVEL,
            name="Doorbell song",
            icon="mdi:thermometer-lines",
            custom_configs=localtuya_selector(
                {
                    "red": "Red",
                    "greed": "Green",
                    "blue": "Blue",
                    "yellow": "Yellow",
                    "purple": "Purple",
                    "white": "White",
                }
            ),
        ),
    ),
    # EV Charcher
    # https://developer.tuya.com/en/docs/iot/categoryqn?id=Kaiuz18kih0sm
    DeviceCategory.QCCDZ: (
        LocalTuyaEntity(
            translation_key="mode",
            id=DPCode.WORK_MODE,
            name="Mode",
            icon="mdi:cog",
            custom_configs=localtuya_selector(
                {
                    "charge_now": "NOW",
                    "charge_pct": "PCT",
                    "charge_energy": "Energy",
                    "charge_schedule": "Schedule",
                }
            ),
        ),
        LocalTuyaEntity(
            translation_key="online_state",
            id=DPCode.ONLINE_STATE,
            name="Online state",
            icon="mdi:cog",
            custom_configs=localtuya_selector(
                {"online": "online", "offline": "offline"}
            ),
        ),
        LocalTuyaEntity(
            translation_key="charge_state",
            id=DPCode.CHARGINGOPERATION,
            name="Charge State",
            icon="mdi:cog",
            custom_configs=localtuya_selector(
                {
                    "OpenCharging": "Open charging",
                    "CloseCharging": "Close charging",
                    "WaitOperation": "Wait for operation",
                }
            ),
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Heater
    # https://developer.tuya.com/en/docs/iot/categoryqn?id=Kaiuz18kih0sm
    DeviceCategory.QN: (
        LocalTuyaEntity(
            translation_key="temperature_level",
            id=DPCode.LEVEL,
            name="Temperature Level",
            icon="mdi:thermometer-lines",
            custom_configs=localtuya_selector(
                {"1": "Level 1", "2": " Levell 2", "3": " Level 3"}
            ),
        ),
        LocalTuyaEntity(
            translation_key="set_countdown",
            id=DPCode.COUNTDOWN,
            name="Set Countdown",
            icon="mdi:timer-cog-outline",
            custom_configs=localtuya_selector(COUNT_DOWN),
        ),
        LocalTuyaEntity(
            translation_key="set_countdown",
            id=DPCode.COUNTDOWN_SET,
            name="Set Countdown",
            icon="mdi:timer-cog-outline",
            custom_configs=localtuya_selector(COUNT_DOWN_HOURS),
        ),
    ),
    # Generic products, EV Charger
    # https://support.tuya.com/en/help/_detail/K9g77zfmlnwal
    DeviceCategory.QT: (
        LocalTuyaEntity(
            translation_key="charge_pattern",
            id=DPCode.CHARGE_PATTERN,
            name="Charge Pattern",
            icon="mdi:car-shift-pattern",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_selector(
                {
                    "netversion": "Netversion",
                    "standalone": "Standalone",
                    "standalone_reserved": "Standalone Reserved",
                    "plug_and_charge": "Plug and Charge",
                }
            ),
        ),
        LocalTuyaEntity(
            translation_key="measurement_model",
            id=DPCode.MEASUREMENT_MODEL,
            name="Measurement Model",
            icon="mdi:call-merge",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_selector(
                {"internal_meter": "Internal", "external_meter": "External"}
            ),
        ),
        LocalTuyaEntity(
            translation_key="earth_test",
            id=DPCode.EARTH_TEST,
            name="Earth Test",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_selector(
                {"enabled_energy": "Enable", "forbidden_energy": "Disable"}
            ),
        ),
        LocalTuyaEntity(
            translation_key="pen_protect",
            id=DPCode.PEN_PROTECT,
            name="Pen Protect",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_selector(
                {"enabled_energy": "Enable", "forbidden_energy": "Disable"}
            ),
        ),
        LocalTuyaEntity(
            translation_key="network",
            id=DPCode.NETWORK_MODEL,
            name="Network",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_selector({"LAN": "LAN", "4G": "4G"}),
        ),
    ),
    # Weather Station
    DeviceCategory.QXJ: (
        LocalTuyaEntity(
            translation_key="temperature_unit",
            id=DPCode.TEMP_UNIT_CONVERT,
            name="Temperature unit",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_selector({"c": "c", "f": "f"}),
        ),
        LocalTuyaEntity(
            translation_key="windspeed_unit",
            id=DPCode.WINDSPEED_UNIT_CONVERT,
            name="Windspeed unit",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_selector(
                {"kmph": "kmph", "mph": "mph", "mps": "mps", "knots": "knots"}
            ),
        ),
        LocalTuyaEntity(
            translation_key="pressure_unit",
            id=DPCode.PRESSURE_UNIT_CONVERT,
            name="Pressure unit",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_selector(
                {"hpa": "hpa", "inhg": "inhg", "mmhg": "mmhg"}
            ),
        ),
        LocalTuyaEntity(
            translation_key="time_format",
            id=DPCode.TIME_FORMAT,
            name="Time Format",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_selector({"12Hr": "12Hr", "24Hr": "24Hr"}),
        ),
        LocalTuyaEntity(
            translation_key="dm",
            id=DPCode.DM,
            name="DM",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_selector({"D_M": "D_M", "M_D": "M_D"}),
        ),
    ),
    # Siren Alarm
    # https://developer.tuya.com/en/docs/iot/categorysgbj?id=Kaiuz37tlpbnu
    DeviceCategory.SGBJ: (
        LocalTuyaEntity(
            translation_key="volume",
            id=DPCode.ALARM_VOLUME,
            name="Volume",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_selector(
                {"low": "LOW", "middle": "MIDDLE", "high": "HIGH", "mute": "MUTE"}
            ),
        ),
        LocalTuyaEntity(
            translation_key="state",
            id=DPCode.ALARM_STATE,
            name="State",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_selector(
                {
                    "alarm_sound": "Sound",
                    "alarm_light": "Light",
                    "alarm_sound_light": "Sound and Light",
                    "normal": "NNORMAL",
                }
            ),
        ),
        LocalTuyaEntity(
            translation_key="brightness",
            id=DPCode.BRIGHT_STATE,
            name="Brightness",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_selector(
                {"low": "LOW", "middle": "MIDDLE", "high": "HIGH", "strong": "MAX"}
            ),
        ),
        LocalTuyaEntity(
            translation_key="alarm_setting",
            id=DPCode.ALARM_SETTING,
            name="Alarm Setting",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_selector(
                {"0": "Setting 1", "0": "Setting 2", "2": "Setting 3", "3": "Setting 4"}
            ),
        ),
        LocalTuyaEntity(
            translation_key="alarm_setting",
            id=DPCode.ALARMTYPE,
            name="Alarm Setting",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_selector(
                {
                    "1": "1",
                    "2": "2",
                    "3": "3",
                    "4": "4",
                    "5": "5",
                    "6": "6",
                    "7": "7",
                    "8": "8",
                    "9": "9",
                    "10": "10",
                    "11": "11",
                    "12": "12",
                }
            ),
        ),
    ),
    # Electric blanket
    DeviceCategory.DR: (
        LocalTuyaEntity(
            translation_key="blanket_level",
            id=DPCode.LEVEL,
            icon="mdi:thermometer-lines",
            name="Blanket Level",
            custom_configs=localtuya_selector(
                {"1": "Level 1", "2": "Level 2", "3": "Level 3"}
            ),
        ),
        LocalTuyaEntity(
            translation_key="side_a_level",
            id=DPCode.LEVEL_1,
            icon="mdi:thermometer-lines",
            name="Side A Level",
            custom_configs=localtuya_selector(
                {"1": "Level 1", "2": "Level 2", "3": "Level 3"}
            ),
        ),
        LocalTuyaEntity(
            translation_key="side_b_level",
            id=DPCode.LEVEL_2,
            icon="mdi:thermometer-lines",
            name="Side B Level",
            custom_configs=localtuya_selector(
                {"1": "Level 1", "2": "Level 2", "3": "Level 3"}
            ),
        ),
    ),
    # Electric desk
    DeviceCategory.SJZ: (
        LocalTuyaEntity(
            translation_key="desk_level",
            id=DPCode.LEVEL,
            name="Desk Level",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_selector({"1": "1", "2": "2", "3": "3", "4": "4"}),
        ),
        LocalTuyaEntity(
            translation_key="desk_up_down",
            id=DPCode.UP_DOWN,
            name="Desk Up/Down",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_selector({"up": "Up", "down": "Down"}),
        ),
    ),
    # Smart Camera
    # https://developer.tuya.com/en/docs/iot/categorysp?id=Kaiuz35leyo12
    DeviceCategory.SP: (
        LocalTuyaEntity(
            translation_key="working_mode",
            id=DPCode.IPC_WORK_MODE,
            entity_category=EntityCategory.CONFIG,
            name="Working mode",
            custom_configs=localtuya_selector({"0": "Low Power", "1": "Continuous"}),
        ),
        LocalTuyaEntity(
            translation_key="decibel_sensitivity",
            id=DPCode.DECIBEL_SENSITIVITY,
            icon="mdi:volume-vibrate",
            entity_category=EntityCategory.CONFIG,
            name="Decibel Sensitivity",
            custom_configs=localtuya_selector(
                {"0": "Low Sensitivity", "1": "High Sensitivity"}
            ),
        ),
        LocalTuyaEntity(
            translation_key="record_mode",
            id=DPCode.RECORD_MODE,
            icon="mdi:record-rec",
            entity_category=EntityCategory.CONFIG,
            name="Record Mode",
            custom_configs=localtuya_selector(
                {"1": "Record Events Only", "2": "Always Record"}
            ),
        ),
        LocalTuyaEntity(
            translation_key="ir_night_vision",
            id=DPCode.BASIC_NIGHTVISION,
            icon="mdi:theme-light-dark",
            entity_category=EntityCategory.CONFIG,
            name="IR Night Vision",
            custom_configs=localtuya_selector({"0": "Auto", "1": "OFF", "2": "ON"}),
        ),
        LocalTuyaEntity(
            translation_key="anti_flicker",
            id=DPCode.BASIC_ANTI_FLICKER,
            icon="mdi:image-outline",
            entity_category=EntityCategory.CONFIG,
            name="Anti-Flicker",
            custom_configs=localtuya_selector(
                {"0": "Disable", "1": "50 Hz", "2": "60 Hz"}
            ),
        ),
        LocalTuyaEntity(
            translation_key="motion_sensitivity",
            id=DPCode.MOTION_SENSITIVITY,
            icon="mdi:motion-sensor",
            entity_category=EntityCategory.CONFIG,
            name="Motion Sensitivity",
            custom_configs=localtuya_selector({"0": "Low", "1": "Medium", "2": "High"}),
        ),
        LocalTuyaEntity(
            translation_key="ptz_control",
            id=DPCode.PTZ_CONTROL,
            icon="mdi:image-filter-tilt-shift",
            entity_category=EntityCategory.CONFIG,
            name="PTZ control",
            custom_configs=localtuya_selector(
                {
                    "0": "UP",
                    "1": "Upper Right",
                    "2": "Right",
                    "3": "Bottom Right",
                    "4": "Down",
                    "5": "Bottom Left",
                    "6": "Left",
                    "7": "Upper Left",
                }
            ),
        ),
        LocalTuyaEntity(
            translation_key="brightness_mode",
            id=DPCode.FLIGHT_BRIGHT_MODE,
            entity_category=EntityCategory.CONFIG,
            name="Brightness mode",
            custom_configs=localtuya_selector({"0": "Manual", "1": "Auto"}),
        ),
        LocalTuyaEntity(
            translation_key="pir_sensitivity",
            id=DPCode.PIR_SENSITIVITY,
            icon="mdi:ray-start-arrow",
            entity_category=EntityCategory.CONFIG,
            name="PIR Sensitivity",
            custom_configs=localtuya_selector({"0": "Low", "1": "Medium", "2": "High"}),
        ),
    ),
    # Dimmer Switch
    # https://developer.tuya.com/en/docs/iot/categorytgkg?id=Kaiuz0ktx7m0o
    DeviceCategory.TGKG: (
        LocalTuyaEntity(
            translation_key="power_on_behavior",
            id=DPCode.RELAY_STATUS,
            icon="mdi:circle-double",
            entity_category=EntityCategory.CONFIG,
            name="Power-on behavior",
            custom_configs=localtuya_selector(
                {"on": "ON", "off": "OFF", "memory": "Last State"}
            ),
            condition_contains_any=["on", "off", "memory"],
        ),
        LocalTuyaEntity(
            translation_key="power_on_behavior",
            id=DPCode.RELAY_STATUS,
            icon="mdi:circle-double",
            entity_category=EntityCategory.CONFIG,
            name="Power-on behavior",
            custom_configs=localtuya_selector(
                {"0": "ON", "1": "OFF", "2": "Last State"}
            ),
        ),
        LocalTuyaEntity(
            translation_key="light_mode",
            id=DPCode.LIGHT_MODE,
            entity_category=EntityCategory.CONFIG,
            name="Light Mode",
            custom_configs=localtuya_selector(
                {"relay": "State", "pos": "Position", "none": "OFF"}
            ),
        ),
        LocalTuyaEntity(
            translation_key="led_type_1",
            id=DPCode.LED_TYPE_1,
            entity_category=EntityCategory.CONFIG,
            name="Led Type 1",
            custom_configs=localtuya_selector(
                {"led": "Led", "incandescent": "Incandescent", "halogen": "Halogen"}
            ),
        ),
        LocalTuyaEntity(
            translation_key="led_type_2",
            id=DPCode.LED_TYPE_2,
            entity_category=EntityCategory.CONFIG,
            name="Led Type 2",
            custom_configs=localtuya_selector(
                {"led": "Led", "incandescent": "Incandescent", "halogen": "Halogen"}
            ),
        ),
        LocalTuyaEntity(
            translation_key="led_type_3",
            id=DPCode.LED_TYPE_3,
            entity_category=EntityCategory.CONFIG,
            name="Led Type 3",
            custom_configs=localtuya_selector(
                {"led": "Led", "incandescent": "Incandescent", "halogen": "Halogen"}
            ),
        ),
    ),
    # Dimmer
    # https://developer.tuya.com/en/docs/iot/tgq?id=Kaof8ke9il4k4
    DeviceCategory.TGQ: (
        LocalTuyaEntity(
            translation_key="led_type_1",
            id=DPCode.LED_TYPE_1,
            entity_category=EntityCategory.CONFIG,
            name="Led Type 1",
            custom_configs=localtuya_selector(
                {"led": "Led", "incandescent": "Incandescent", "halogen": "Halogen"}
            ),
        ),
        LocalTuyaEntity(
            translation_key="led_type_2",
            id=DPCode.LED_TYPE_2,
            entity_category=EntityCategory.CONFIG,
            name="Led Type 2",
            custom_configs=localtuya_selector(
                {"led": "Led", "incandescent": "Incandescent", "halogen": "Halogen"}
            ),
        ),
    ),
    # Fingerbot
    DeviceCategory.SZJQR: (
        LocalTuyaEntity(
            translation_key="fingerbot_mode",
            id=DPCode.MODE,
            entity_category=EntityCategory.CONFIG,
            name="Fingerbot Mode",
            custom_configs=localtuya_selector(
                {"click": "Click", "switch": "Switch", "toggle": "Toggle"}
            ),
        ),
    ),
    # Robot Vacuum
    # https://developer.tuya.com/en/docs/iot/fsd?id=K9gf487ck1tlo
    DeviceCategory.SD: (
        LocalTuyaEntity(
            translation_key="water_tank_adjustment",
            id=DPCode.CISTERN,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:water-opacity",
            name="Water Tank Adjustment",
            custom_configs=localtuya_selector(
                {"low": "Low", "middle": "Middle", "high": "High", "closed": "Closed"}
            ),
        ),
        LocalTuyaEntity(
            translation_key="dust_collection_mode",
            id=DPCode.COLLECTION_MODE,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:air-filter",
            name="Dust Collection Mode",
            custom_configs=localtuya_selector(
                {"small": "Small", "middle": "Middle", "large": "Large"}
            ),
        ),
        LocalTuyaEntity(
            translation_key="dust_collection_mode",
            id=DPCode.VOICE_LANGUAGE,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:air-filter",
            name="Dust Collection Mode",
            custom_configs=localtuya_selector({"cn": "Chinese", "en": "English"}),
        ),
        LocalTuyaEntity(
            translation_key="direction",
            id=DPCode.DIRECTION_CONTROL,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:arrow-all",
            name="Direction",
            custom_configs=localtuya_selector(
                {
                    "forward": "Forward",
                    "backward": "Backward",
                    "turn_left": "Left",
                    "turn_right": "Right",
                    "stop": "Stop",
                }
            ),
        ),
        LocalTuyaEntity(
            translation_key="mode",
            id=DPCode.MODE,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:layers-outline",
            name="Mode",
            custom_configs=localtuya_selector(
                {
                    "standby": "StandBy",
                    "random": "Random",
                    "smart": "Smart",
                    "wallfollow": "Follow Wall",
                    "mop": "Mop",
                    "spiral": "Spiral",
                    "left_spiral": "Spiral Left",
                    "right_spiral": "Spiral Right",
                    "right_bow": "Bow Right",
                    "left_bow": "Bow Left",
                    "partial_bow": "Bow Partial",
                    "chargego": "Charge",
                }
            ),
        ),
    ),
    # Fan
    # https://developer.tuya.com/en/docs/iot/f?id=K9gf45vs7vkge
    DeviceCategory.FS: (
        LocalTuyaEntity(
            translation_key="mode",
            id=DPCode.MODE,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:cog",
            name="Mode",
            custom_configs=localtuya_selector(
                {"sleep": "Sleep", "normal": "Normal", "nature": "Nature"}
            ),
        ),
        LocalTuyaEntity(
            translation_key="vertical_swing",
            id=DPCode.FAN_VERTICAL,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:format-vertical-align-center",
            name="Vertical swing",
            custom_configs=localtuya_selector(
                {"30": "30 Deg", "60": "60 Deg", "90": "90 Deg"}
            ),
        ),
        LocalTuyaEntity(
            translation_key="horizontal_swing",
            id=DPCode.FAN_HORIZONTAL,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:format-horizontal-align-center",
            name="Horizontal swing",
            custom_configs=localtuya_selector(
                {"30": "30 Deg", "60": "60 Deg", "90": "90 Deg"}
            ),
        ),
        LocalTuyaEntity(
            translation_key="light_mode",
            id=DPCode.WORK_MODE,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:ceiling-fan-light",
            name="Light mode",
            custom_configs=localtuya_selector(
                {"white": "White", "colour": "Colour", "colourful": "Colourful"}
            ),
        ),
        LocalTuyaEntity(
            translation_key="countdown",
            id=DPCode.COUNTDOWN,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:timer-cog-outline",
            name="Countdown",
            custom_configs=localtuya_selector(COUNT_DOWN),
        ),
        LocalTuyaEntity(
            translation_key="countdown",
            id=DPCode.COUNTDOWN_SET,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:timer-cog-outline",
            name="Countdown",
            custom_configs=localtuya_selector(COUNT_DOWN_HOURS),
        ),
        # Gratkit dryer v2 https://github.com/xZetsubou/hass-localtuya/issues/501
        LocalTuyaEntity(
            translation_key="light",
            id=DPCode.LEDLIGHT,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:led-strip",
            name="Light",
            custom_configs=localtuya_selector(
                {
                    "0": "OFF",
                    "1": "Red",
                    "2": "Green",
                    "3": "Blue",
                    "4": "White",
                    "5": "Yellow",
                    "6": "Cyan",
                    "7": "Purple",
                    "8": "Orange",
                    "9": "Pink",
                    "10": "Rainbow Fade",
                    "11": "Rainbow Blink",
                    "12": "Rainbow Smooth",
                    "13": "13",
                    "14": "14",
                    "15": "15",
                    "16": "16",
                    "17": "17",
                    "18": "18",
                    "19": "19",
                    "20": "20",
                }
            ),
        ),
        LocalTuyaEntity(
            translation_key="material_type",
            id=DPCode.MATERIAL_TYPE,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:kite-outline",
            name="Material Type",
            custom_configs=localtuya_selector(
                {
                    "PETG": "PETG",
                    "PLA_J": "PLA_J",
                    "PC": "PC",
                    "TPU": "TPU",
                    "ABS": "ABS",
                    "DIY2": "DIY2",
                    "PLA": "PLA",
                    "DIY1": "DIY1",
                    "Nylon": "Nylon",
                    "HIPS": "HIPS",
                }
            ),
        ),
    ),
    # Curtain
    # https://developer.tuya.com/en/docs/iot/f?id=K9gf46o5mtfyc
    DeviceCategory.CL: (
        LocalTuyaEntity(
            translation_key="motor_direction",
            id=(DPCode.CONTROL_BACK_MODE, DPCode.CONTROL_BACK),
            name="Motor Direction",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:swap-vertical",
            custom_configs=localtuya_selector({"forward": "Forward", "back": "Back"}),
        ),
        LocalTuyaEntity(
            translation_key="motor_mode",
            id=DPCode.MOTOR_MODE,
            name="Motor Mode",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:cog-transfer",
            custom_configs=localtuya_selector(
                {"contiuation": "Auto", "point": "Manual"}
            ),
        ),
        LocalTuyaEntity(
            translation_key="cover_mode",
            id=DPCode.MODE,
            entity_category=EntityCategory.CONFIG,
            name="Cover Mode",
            custom_configs=localtuya_selector({"morning": "Morning", "night": "Night"}),
        ),
    ),
    # Humidifier
    # https://developer.tuya.com/en/docs/iot/categoryjsq?id=Kaiuz1smr440b
    DeviceCategory.JSQ: (
        LocalTuyaEntity(
            translation_key="spraying_mode",
            id=DPCode.SPRAY_MODE,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:spray",
            name="Spraying mode",
            custom_configs=localtuya_selector(
                {
                    "auto": "AUTO",
                    "health": "Health",
                    "baby": "BABY",
                    "sleep": "SLEEP",
                    "humidity": "HUMIDITY",
                    "work": "WORK",
                }
            ),
        ),
        LocalTuyaEntity(
            translation_key="spraying_level",
            id=DPCode.LEVEL,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:spray",
            name="Spraying level",
            custom_configs=localtuya_selector(
                {
                    "level_1": "LEVEL 1",
                    "level_2": "LEVEL 2",
                    "level_3": "LEVEL 3",
                    "level_4": "LEVEL 4",
                    "level_5": "LEVEL 5",
                    "level_6": "LEVEL 6",
                    "level_7": "LEVEL 7",
                    "level_8": "LEVEL 8",
                    "level_9": "LEVEL 9",
                    "level_10": "LEVEL 10",
                }
            ),
        ),
        LocalTuyaEntity(
            translation_key="mood_light",
            id=DPCode.MOODLIGHTING,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:lightbulb-multiple",
            name="Mood light",
            custom_configs=localtuya_selector(
                {"1": "1", "2": "2", "3": "3", "4": "4", "5": "5"}
            ),
        ),
        LocalTuyaEntity(
            translation_key="countdown",
            id=DPCode.COUNTDOWN,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:timer-cog-outline",
            name="Countdown",
            custom_configs=localtuya_selector(COUNT_DOWN),
        ),
        LocalTuyaEntity(
            translation_key="countdown",
            id=DPCode.COUNTDOWN_SET,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:timer-cog-outline",
            name="Countdown",
            custom_configs=localtuya_selector(COUNT_DOWN_HOURS),
        ),
    ),
    # Air Purifier
    # https://developer.tuya.com/en/docs/iot/f?id=K9gf46h2s6dzm
    DeviceCategory.KJ: (
        LocalTuyaEntity(
            translation_key="countdown",
            id=DPCode.COUNTDOWN,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:timer-cog-outline",
            name="Countdown",
            custom_configs=localtuya_selector(COUNT_DOWN),
        ),
        LocalTuyaEntity(
            translation_key="countdown",
            id=DPCode.COUNTDOWN_SET,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:timer-cog-outline",
            name="Countdown",
            custom_configs=localtuya_selector(COUNT_DOWN_HOURS),
        ),
    ),
    # Dehumidifier
    # https://developer.tuya.com/en/docs/iot/categorycs?id=Kaiuz1vcz4dha
    DeviceCategory.CS: (
        LocalTuyaEntity(
            translation_key="countdown",
            id=DPCode.COUNTDOWN_SET,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:timer-cog-outline",
            name="Countdown",
            custom_configs=localtuya_selector(
                {"cancel": "Disable", "2h": "2 Hours", "4h": "4 Hours", "8h": "8 Hours"}
            ),
        ),
        LocalTuyaEntity(
            translation_key="target_humidity",
            id=DPCode.DEHUMIDITY_SET_ENUM,
            name="Target Humidity",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:water-percent",
            custom_configs=localtuya_selector(
                {"10": "10", "20": "20", "30": "30", "40": "40", "50": "50", "60": "60"}
            ),
        ),
        LocalTuyaEntity(
            translation_key="intensity",
            id=DPCode.SPRAY_VOLUME,
            name="Intensity",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:volume-source",
            custom_configs=localtuya_selector(
                {"small": "Low", "middle": "Medium", "large": "High"}
            ),
        ),
        LocalTuyaEntity(
            translation_key="fan_speed",
            id=DPCode.FAN_SPEED_ENUM,
            name="Fan Speed",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:fan",
            custom_configs=localtuya_selector({"low": "Low", "high": "High"}),
        ),
    ),
    # Water Detector
    # https://developer.tuya.com/en/docs/iot/categorysj?id=Kaiuz3iub2sli
    DeviceCategory.SJ: (
        LocalTuyaEntity(
            translation_key="temperature_unit",
            id=(DPCode.C_F, DPCode.TEMP_UNIT_CONVERT),
            name="Temperature Unit",
            icon="mdi:cog",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_selector({"c": "Celsius", "f": "Fahrenheit"}),
        ),
    ),
    # Water Valve
    DeviceCategory.SFKZQ: (
        LocalTuyaEntity(
            translation_key="smart_weather_mode",
            id=DPCode.SMART_WEATHER,
            name="Smart Weather Mode",
            icon="mdi:cog",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_selector(
                {"cloudy": "Cloudy", "rainy": "Rainy", "snowy": "Snowy"}
            ),
        ),
        LocalTuyaEntity(
            translation_key="weather_delay",
            id=DPCode.WEATHER_DELAY,
            name="Weather Delay",
            icon="mdi:weather-rainy",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_selector({"0": "0", "1": "1", "2": "2", "3": "3"}),
        ),
    ),
    # Micro Storage Inverter
    DeviceCategory.XNYJCN: (
        LocalTuyaEntity(
            translation_key="inverter_work_mode",
            id=DPCode.WORK_MODE,
            name="Inverter Work Mode",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_selector(
                {"self_use": "Self Use", "feed_in": "Feed In", "backup": "Backup"}
            ),
        ),
    ),
    # sous vide cookers
    # https://developer.tuya.com/en/docs/iot/f?id=K9r2v9hgmyk3h
    DeviceCategory.MZJ: (
        LocalTuyaEntity(
            translation_key="cooking_mode",
            id=DPCode.MODE,
            entity_category=EntityCategory.CONFIG,
            name="Cooking Mode",
            custom_configs=localtuya_selector(
                {
                    "vegetables": "Vegetables",
                    "meat": "Meat",
                    "shrimp": "Shrimp",
                    "fish": "Fish",
                    "chicken": "Chicken",
                    "drumsticks": "Drumsticks",
                    "beef": "Beef",
                    "rice": "Rice",
                }
            ),
        ),
    ),
    # PIR Detector
    # https://developer.tuya.com/en/docs/iot/categorypir?id=Kaiuz3ss11b80
    DeviceCategory.PIR: (
        LocalTuyaEntity(
            translation_key="mode",
            id=DPCode.MOD,
            icon="mdi:cog",
            entity_category=EntityCategory.CONFIG,
            name="Mode",
            custom_configs=localtuya_selector(
                {"mode_auto": "AUTO", "mode_on": "ON", "mode_off": "OFF"}
            ),
        ),
        LocalTuyaEntity(
            translation_key="pir_sensitivity",
            id=DPCode.PIR_SENSITIVITY,
            icon="mdi:ray-start-arrow",
            entity_category=EntityCategory.CONFIG,
            name="PIR Sensitivity",
            custom_configs=localtuya_selector(
                {"low": "Low", "middle": "Middle", "high": "High"}
            ),
        ),
        LocalTuyaEntity(
            translation_key="reset_time",
            id=DPCode.PIR_TIME,
            icon="mdi:timer-sand",
            entity_category=EntityCategory.CONFIG,
            name="Reset Time",
            custom_configs=localtuya_selector(
                {"30s": "30 Seconds", "60s": "60 Seconds", "120s": "120 Seconds"}
            ),
        ),
    ),
    # Thermostat
    # https://developer.tuya.com/en/docs/iot/f?id=K9gf45ld5l0t9
    DeviceCategory.WK: (
        LocalTuyaEntity(
            translation_key="temperature_sensor",
            id=DPCode.SENSORTYPE,
            entity_category=EntityCategory.CONFIG,
            name="Temperature sensor",
            custom_configs=localtuya_selector(
                {"0": "Internal", "1": "External", "2": "Both"}
            ),
        ),
    ),
    # Temperature and Humidity Sensor
    # https://developer.tuya.com/en/docs/iot/categorywsdcg?id=Kaiuz3hinij34
    DeviceCategory.WSDCG: (
        LocalTuyaEntity(
            translation_key="temperature_unit",
            id=(DPCode.C_F, DPCode.TEMP_UNIT_CONVERT),
            name="Temperature Unit",
            icon="mdi:cog",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_selector({"c": "Celsius", "f": "Fahrenheit"}),
        ),
        # LocalTuyaEntity(
        #     id=DPCode.TEMP_ALARM,
        #     name="Temperature Alarm",
        #     entity_category=EntityCategory.CONFIG,
        #     icon="mdi:bell-alert",
        #     custom_configs=localtuya_selector(
        #         {"loweralarm": "Low", "upperalarm": "High", "cancel": "Cancel"}
        #     ),
        # ),
        # LocalTuyaEntity(
        #     id=DPCode.HUM_ALARM,
        #     name="Humidity Alarm",
        #     icon="mdi:bell-alert",
        #     entity_category=EntityCategory.CONFIG,
        #     custom_configs=localtuya_selector(
        #         {"loweralarm": "Low", "upperalarm": "High", "cancel": "Cancel"}
        #     ),
        # ),
    ),
    # Alarm Host
    # https://developer.tuya.com/en/docs/iot/categorymal?id=Kaiuz33clqxaf
    DeviceCategory.MAL: (
        LocalTuyaEntity(
            translation_key="zone_attribute",
            id=DPCode.ZONE_ATTRIBUTE,
            entity_category=EntityCategory.CONFIG,
            name="Zone Attribute",
            custom_configs=localtuya_selector(
                {
                    "MODE_HOME_ARM": "Home Arm",
                    "MODE_ARM": "Arm",
                    "MODE_24": "24H",
                    "MODE_DOORBELL": "Doorbell",
                    "MODE_24_SILENT": "Silent",
                    "HOME_ARM_NO_DELAY": "Home, Arm No delay",
                    "ARM_NO_DELAY": "Arm No delay",
                }
            ),
        ),
        LocalTuyaEntity(
            translation_key="host_status",
            id=DPCode.MASTER_STATE,
            entity_category=EntityCategory.CONFIG,
            name="Host Status",
            custom_configs=localtuya_selector({"normal": "Normal", "alarm": "Alarm"}),
        ),
        LocalTuyaEntity(
            translation_key="sub_device_category",
            id=DPCode.SUB_CLASS,
            entity_category=EntityCategory.CONFIG,
            name="Sub-device category",
            custom_configs=localtuya_selector(
                {
                    "remote_controller": "Remote Controller",
                    "detector": "Detector",
                    "socket": "Socket",
                }
            ),
        ),
        LocalTuyaEntity(
            translation_key="sub_device_type",
            id=DPCode.SUB_TYPE,
            entity_category=EntityCategory.CONFIG,
            name="Sub-device type",
            custom_configs=localtuya_selector(
                {
                    "OTHER": "Other",
                    "DOOR": "Door",
                    "PIR": "Pir",
                    "SOS": "SoS",
                    "ROOM": "Room",
                    "WINDOW": "Window",
                    "BALCONY": "Balcony",
                    "FENCE": "Fence",
                    "SMOKE": "Smoke",
                    "GAS": "Gas",
                    "CO": "CO",
                    "WATER": "Water",
                }
            ),
        ),
    ),
    # Smart Water Meter
    # https://developer.tuya.com/en/docs/iot/f?id=Ka8n052xu7w4c
    DeviceCategory.ZNSB: (
        LocalTuyaEntity(
            translation_key="report_period",
            id=DPCode.REPORT_PERIOD_SET,
            entity_category=EntityCategory.CONFIG,
            name="Report Period",
            custom_configs=localtuya_selector(
                {
                    "1h": "1 Hours",
                    "2h": "2 Hours",
                    "3h": "3 Hours",
                    "4h": "4 Hours",
                    "6h": "6 Hours",
                    "8h": "8 Hours",
                    "12h": "12 Hours",
                    "24h": "24 Hours",
                    "48h": "48 Hours",
                    "72h": "72 Hours",
                }
            ),
            icon="mdi:file-chart-outline",
        ),
    ),
    # HDMI Sync Box A1
    DeviceCategory.HDMIPMTBQ: (
        LocalTuyaEntity(
            translation_key="video_type",
            id=DPCode.VIDEO_SCENE,
            entity_category=EntityCategory.CONFIG,
            name="Video Type",
            icon="mdi:camera-burst",
            custom_configs=localtuya_selector({"game": "Gaming", "movie": "Movies"}),
        ),
        LocalTuyaEntity(
            translation_key="video_mode",
            id=DPCode.VIDEO_MODE,
            entity_category=EntityCategory.CONFIG,
            name="Video Mode",
            icon="mdi:format-wrap-square",
            custom_configs=localtuya_selector(
                {
                    "nor_closed": "Nor Closed",
                    "multiple_colour": "Multi Colors",
                    "single_colour": "Single Color",
                }
            ),
        ),
        LocalTuyaEntity(
            translation_key="intensity",
            id=DPCode.VIDEO_INTENSITY,
            entity_category=EntityCategory.CONFIG,
            name="Intensity",
            icon="mdi:television-ambient-light",
            custom_configs=localtuya_selector(
                {
                    "low": "Low",
                    "middle": "Middle",
                    "high": "High",
                    "music": "Music",
                }
            ),
        ),
        LocalTuyaEntity(
            translation_key="start_position",
            id=DPCode.STRIP_INPUT_POS,
            entity_category=EntityCategory.CONFIG,
            name="Start Position",
            icon="mdi:vector-square-minus",
            custom_configs=localtuya_selector(
                {"low_right": "Low Right", "low_left": "Low Left"}
            ),
        ),
        LocalTuyaEntity(
            translation_key="strip_direction",
            id=DPCode.STRIP_DIRECTION,
            entity_category=EntityCategory.CONFIG,
            name="Strip Direction",
            icon="mdi:subdirectory-arrow-right",
            custom_configs=localtuya_selector(
                {"clockwise": "Clockwise", "anti_clockwise": "Counter-Clockwise"}
            ),
        ),
        LocalTuyaEntity(
            translation_key="tv_size",
            id=DPCode.TV_SIZE,
            entity_category=EntityCategory.CONFIG,
            name="TV Size",
            icon="mdi:move-resize",
            custom_configs=localtuya_selector(
                {
                    "55_to_64_inch": "55 - 64 Inches",
                    "65_to_74_inch": "65 - 74 Inches",
                    "above_75_inch": "75 Inches or Above",
                }
            ),
        ),
    ),
    # Lawn mower
    DeviceCategory.GCJ: (
        LocalTuyaEntity(
            translation_key="control",
            id=DPCode.MACHINECONTROLCMD,
            name="Control",
            custom_configs=localtuya_selector(
                {
                    "PauseWork": "PauseWork",
                    "CancelWork": "CancelWork",
                    "ContinueWork": "ContinueWork",
                    "StartMowing": "StartMowing",
                    "StartFixedMowing": "StartFixedMowing",
                    "StartReturnStation": "StartReturnStation",
                }
            ),
        ),
        LocalTuyaEntity(
            translation_key="password",
            id=DPCode.MACHINEPASSWORD,
            name="Password",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:lock-question-outline",
        ),
    ),
}
# Wireless Switch  # also can come as knob switch. # and scene switch.
# https://developer.tuya.com/en/docs/iot/wxkg?id=Kbeo9t3ryuqm5
SELECTS[DeviceCategory.WXKG] = (
    LocalTuyaEntity(
        translation_key="display_mode",
        id=DPCode.WORK_MODE,
        name="Display mode",
        icon="mdi:square-outline",
        entity_category=EntityCategory.CONFIG,
        custom_configs=localtuya_selector(
            {"brightness": "Brightness", "temperature": "Temperature"}
        ),
    ),
    LocalTuyaEntity(
        translation_key="switch_1",
        id=(DPCode.SWITCH1_VALUE, DPCode.SWITCH_TYPE_1),
        name="Switch 1",
        icon="mdi:square-outline",
        entity_category=EntityCategory.CONFIG,
        custom_configs=localtuya_selector(
            {
                "single_click": "Single click",
                "double_click": "Double click",
                "long_press": "Long Press",
            }
        ),
        condition_contains_any=["single_click", "double_click", "long_press"],
    ),
    LocalTuyaEntity(
        translation_key="switch_2",
        id=(DPCode.SWITCH2_VALUE, DPCode.SWITCH_TYPE_2),
        name="Switch 2",
        icon="mdi:palette-outline",
        entity_category=EntityCategory.CONFIG,
        custom_configs=localtuya_selector(
            {
                "single_click": "Single click",
                "double_click": "Double click",
                "long_press": "Long Press",
            }
        ),
        condition_contains_any=["single_click", "double_click", "long_press"],
    ),
    LocalTuyaEntity(
        translation_key="switch_3",
        id=(DPCode.SWITCH3_VALUE, DPCode.SWITCH_TYPE_3),
        name="Switch 3",
        icon="mdi:palette-outline",
        entity_category=EntityCategory.CONFIG,
        custom_configs=localtuya_selector(
            {
                "single_click": "Single click",
                "double_click": "Double click",
                "long_press": "Long Press",
            }
        ),
        condition_contains_any=["single_click", "double_click", "long_press"],
    ),
    LocalTuyaEntity(
        translation_key="switch_4",
        id=(DPCode.SWITCH4_VALUE, DPCode.SWITCH_TYPE_4),
        name="Switch 4",
        icon="mdi:palette-outline",
        entity_category=EntityCategory.CONFIG,
        custom_configs=localtuya_selector(
            {
                "single_click": "Single click",
                "double_click": "Double click",
                "long_press": "Long Press",
            }
        ),
        condition_contains_any=["single_click", "double_click", "long_press"],
    ),
    LocalTuyaEntity(
        translation_key="switch_5",
        id=(DPCode.SWITCH5_VALUE, DPCode.SWITCH_TYPE_5),
        name="Switch 5",
        icon="mdi:palette-outline",
        entity_category=EntityCategory.CONFIG,
        custom_configs=localtuya_selector(
            {
                "single_click": "Single click",
                "double_click": "Double click",
                "long_press": "Long Press",
            }
        ),
        condition_contains_any=["single_click", "double_click", "long_press"],
    ),
    LocalTuyaEntity(
        translation_key="mode",
        id=DPCode.MODE,
        name="Mode",
        icon="mdi:cog",
        entity_category=EntityCategory.CONFIG,
        custom_configs=localtuya_selector(
            {"remote_control": "Remote", "wireless_switch": "Wireless"}
        ),
        condition_contains_any=["remote_control", "wireless_switch"],
    ),
    *SELECTS[DeviceCategory.KG],
)

# Scene Switch
# https://developer.tuya.com/en/docs/iot/f?id=K9gf7nx6jelo8
SELECTS[DeviceCategory.CJKG] = SELECTS[DeviceCategory.KG]

# Fan wall switch
# For Power-on behavior
SELECTS[DeviceCategory.FSKG] = SELECTS[DeviceCategory.KG]

# Socket (duplicate of `kg`)
# https://developer.tuya.com/en/docs/iot/s?id=K9gf7o5prgf7s
SELECTS[DeviceCategory.CZ] = SELECTS[DeviceCategory.KG]

# Power Socket (duplicate of `kg`)
# https://developer.tuya.com/en/docs/iot/s?id=K9gf7o5prgf7s
SELECTS[DeviceCategory.PC] = SELECTS[DeviceCategory.KG]

SELECTS[DeviceCategory.TDQ] = SELECTS[DeviceCategory.KG]

# Heater
SELECTS[DeviceCategory.RS] = SELECTS[DeviceCategory.KT]

# Smart Camera - Low power consumption camera (duplicate of `sp`)
SELECTS[DeviceCategory.DGHSXJ] = SELECTS[DeviceCategory.SP]
