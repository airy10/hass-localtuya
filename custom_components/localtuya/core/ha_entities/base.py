from enum import StrEnum
from dataclasses import dataclass, field
from typing import Any

from homeassistant.const import (
    CONF_FRIENDLY_NAME,
    CONF_ICON,
    CONF_ENTITY_CATEGORY,
    CONF_DEVICE_CLASS,
    Platform,
    EntityCategory,
)
from ...const import (
    CONF_CLEAN_AREA_DP,
    CONF_DPS_STRINGS,
    CONF_STATE_CLASS,
    DPType,
)


# Obtain values from cloud data.
@dataclass
class CLOUD_VALUE:
    """Retrieve a value from stored cloud data

    `default_value`: The value that will be used if it fails to retrieve from the cloud.\n
    `dp_config(str)`: The dp config key that will be used to look for the values into it.\n
    `value_key(str)`: The "key" name of the targeted value.\n
    `prefer_type`: Convert values
            Integer: Type(value) ( int, float or str ).\n
            Enums: convert the values to [dict or str split by comma, default is list].\n
    `remap_values(dict)`: Used to remap dict values, if prefer_type is dict.\n
    `reverse_dict(bool)`: Reverse dict keys, value, if prefer_type is dict.\n
    `scale(bool)`: For integers, scale final value.\n
    """

    default_value: Any
    dp_config: str
    value_key: str
    prefer_type: type = None
    remap_values: dict[str, Any] = field(default_factory=dict)
    reverse_dict: bool = False
    scale: bool = False


class LocalTuyaEntity:
    """
    Localtuya entity config.
    Each platform has unique custom_configs to give the required data to validate entity setups.
    e.g. Switch req( Friendly_Name and DP(Code) )
    """

    def __init__(
        self,
        name: str = "",
        icon: str = "",
        entity_category="None",
        device_class=None,
        state_class=None,
        custom_configs: dict[str, Any | tuple[Any, CLOUD_VALUE]] = {},
        condition_contains_any: list = None,
        **kwargs,
    ):
        # platform, name, icon, entity_category, device_class, *key
        # self.platform = platform
        self.name = name
        self.data = {
            CONF_FRIENDLY_NAME: name,
            CONF_ICON: icon,
            CONF_ENTITY_CATEGORY: entity_category,
        }

        # Optional
        if device_class:
            self.data[CONF_DEVICE_CLASS] = device_class

        # Optional
        if state_class:
            self.data[CONF_STATE_CLASS] = state_class

        self.entity_configs = custom_configs

        self.contains_any = condition_contains_any

        # Replace key with id if needed
        if kwargs.get("key", False):
            kwargs["id"] = kwargs.pop("key")
        # e.g.e CONF_ID etc..

        self.localtuya_conf = kwargs


class DeviceCategory(StrEnum):
    """Tuya device categories.

    https://developer.tuya.com/en/docs/iot/standarddescription?id=K9i5ql6waswzq
    """

    AMY = "amy"
    """Massage chair"""
    BGL = "bgl"
    """Wall-hung boiler"""
    BH = "bh"
    """Smart kettle

    https://developer.tuya.com/en/docs/iot/fbh?id=K9gf484m21yq7
    """
    BX = "bx"
    """Refrigerator"""
    BXX = "bxx"
    """Safe box"""
    CJKG = "cjkg"
    """Scene switch"""
    CKMKZQ = "ckmkzq"
    """Garage door opener

    https://developer.tuya.com/en/docs/iot/categoryckmkzq?id=Kaiuz0ipcboee
    """
    CKQDKG = "ckqdkg"
    """Card switch"""
    CL = "cl"
    """Curtain

    https://developer.tuya.com/en/docs/iot/categorycl?id=Kaiuz1hnpo7df
    """
    CLKG = "clkg"
    """Curtain switch

    https://developer.tuya.com/en/docs/iot/category-clkg?id=Kaiuz0gitil39
    """
    CN = "cn"
    """Milk dispenser"""
    CO2BJ = "co2bj"
    """CO2 detector

    https://developer.tuya.com/en/docs/iot/categoryco2bj?id=Kaiuz3wes7yuy
    """
    COBJ = "cobj"
    """CO detector

    https://developer.tuya.com/en/docs/iot/categorycobj?id=Kaiuz3u1j6q1v
    """
    CS = "cs"
    """Dehumidifier

    https://developer.tuya.com/en/docs/iot/categorycs?id=Kaiuz1vcz4dha
    """
    CWTSWSQ = "cwtswsq"
    """Pet treat feeder"""
    CWWQFSQ = "cwwqfsq"
    """Pet ball thrower"""
    CWWSQ = "cwwsq"
    """Pet feeder

    https://developer.tuya.com/en/docs/iot/categorycwwsq?id=Kaiuz2b6vydld
    """
    CWYSJ = "cwysj"
    """Pet fountain

    https://developer.tuya.com/en/docs/iot/categorycwysj?id=Kaiuz2dfro0nd
    """
    CZ = "cz"
    """Socket"""
    DBL = "dbl"
    """Electric fireplace

    https://developer.tuya.com/en/docs/iot/electric-fireplace?id=Kaiuz2hz4iyp6
    """
    DC = "dc"
    """String lights

    # https://developer.tuya.com/en/docs/iot/dc?id=Kaof7taxmvadu
    """
    DCL = "dcl"
    """Induction cooker"""
    DD = "dd"
    """Strip lights

    https://developer.tuya.com/en/docs/iot/dd?id=Kaof804aibg2l
    """
    DGNBJ = "dgnbj"
    """Multi-functional alarm

    https://developer.tuya.com/en/docs/iot/categorydgnbj?id=Kaiuz3yorvzg3
    """
    DJ = "dj"
    """Light

    https://developer.tuya.com/en/docs/iot/categorydj?id=Kaiuyzy3eheyy
    """
    DLQ = "dlq"
    """Circuit breaker

    https://developer.tuya.com/en/docs/iot/dlq?id=Kb0kidk9enyh8
    """
    DR = "dr"
    """Electric blanket

    https://developer.tuya.com/en/docs/iot/categorydr?id=Kaiuz22dyc66p
    """
    DS = "ds"
    """TV set"""
    FS = "fs"
    """Fan

    https://developer.tuya.com/en/docs/iot/categoryfs?id=Kaiuz1xweel1c
    """
    FSD = "fsd"
    """Ceiling fan light

    https://developer.tuya.com/en/docs/iot/fsd?id=Kaof8eiei4c2v
    """
    FWD = "fwd"
    """Ambiance light

    https://developer.tuya.com/en/docs/iot/ambient-light?id=Kaiuz06amhe6g
    """
    GGQ = "ggq"
    """Irrigator

    https://developer.tuya.com/en/docs/iot/categoryggq?id=Kaiuz1qib7z0k
    """
    GYD = "gyd"
    """Motion sensor light

    https://developer.tuya.com/en/docs/iot/gyd?id=Kaof8a8hycfmy
    """
    GYMS = "gyms"
    """Business lock"""
    HOTELMS = "hotelms"
    """Hotel lock"""
    HPS = "hps"
    """Human presence sensor

    https://developer.tuya.com/en/docs/iot/categoryhps?id=Kaiuz42yhn1hs
    """
    JS = "js"
    """Water purifier"""
    JSQ = "jsq"
    """Humidifier

    https://developer.tuya.com/en/docs/iot/categoryjsq?id=Kaiuz1smr440b
    """
    JTMSBH = "jtmsbh"
    """Smart lock (keep alive)"""
    JTMSPRO = "jtmspro"
    """Residential lock pro"""
    JWBJ = "jwbj"
    """Methane detector

    https://developer.tuya.com/en/docs/iot/categoryjwbj?id=Kaiuz40u98lkm
    """
    KFJ = "kfj"
    """Coffee maker

    https://developer.tuya.com/en/docs/iot/categorykfj?id=Kaiuz2p12pc7f
    """
    KG = "kg"
    """Switch

    https://developer.tuya.com/en/docs/iot/s?id=K9gf7o5prgf7s
    """
    KJ = "kj"
    """Air purifier

    https://developer.tuya.com/en/docs/iot/f?id=K9gf46h2s6dzm
    """
    KQZG = "kqzg"
    """Air fryer"""
    KT = "kt"
    """Air conditioner

    https://developer.tuya.com/en/docs/iot/categorykt?id=Kaiuz0z71ov2n
    """
    KTKZQ = "ktkzq"
    """Air conditioner controller"""
    LDCG = "ldcg"
    """Luminance sensor

    https://developer.tuya.com/en/docs/iot/categoryldcg?id=Kaiuz3n7u69l8
    """
    LILIAO = "liliao"
    """Physiotherapy product"""
    LYJ = "lyj"
    """Drying rack"""
    MAL = "mal"
    """Alarm host

    https://developer.tuya.com/en/docs/iot/categorymal?id=Kaiuz33clqxaf
    """
    MB = "mb"
    """Bread maker"""
    MC = "mc"
    """Door/window controller

    https://developer.tuya.com/en/docs/iot/s?id=K9gf48r5zjsy9
    """
    MCS = "mcs"
    """Contact sensor

    https://developer.tuya.com/en/docs/iot/s?id=K9gf48hm02l8m
    """
    MG = "mg"
    """Rice cabinet"""
    MJJ = "mjj"
    """Towel rack"""
    MK = "mk"
    """Access control

    https://developer.tuya.com/en/docs/iot/s?id=Kb0o2xhlkxbet
    """
    MS = "ms"
    """Residential lock"""
    MS_CATEGORY = "ms_category"
    """Lock accessories"""
    MSP = "msp"
    """Cat toilet

    https://developer.tuya.com/en/docs/iot/s?id=Kakg3srr4ora7
    """
    MZJ = "mzj"
    """Sous vide cooker

    https://developer.tuya.com/en/docs/iot/categorymzj?id=Kaiuz2vy130ux
    """
    NNQ = "nnq"
    """Bottle warmer"""
    NTQ = "ntq"
    """HVAC"""
    PC = "pc"
    """Power strip

    https://developer.tuya.com/en/docs/iot/s?id=K9gf7o5prgf7s
    """
    PHOTOLOCK = "photolock"
    """Audio and video lock"""
    PIR = "pir"
    """Human motion sensor

    https://developer.tuya.com/en/docs/iot/categorypir?id=Kaiuz3ss11b80
    """
    PM2_5 = "pm2.5"
    """PM2.5 detector

    https://developer.tuya.com/en/docs/iot/categorypm25?id=Kaiuz3qof3yfu
    """
    QN = "qn"
    """Heater

    https://developer.tuya.com/en/docs/iot/categoryqn?id=Kaiuz18kih0sm
    """
    RQBJ = "rqbj"
    """Gas alarm

    https://developer.tuya.com/en/docs/iot/categoryrqbj?id=Kaiuz3d162ubw
    """
    RS = "rs"
    """Water heater

    https://developer.tuya.com/en/docs/iot/categoryrs?id=Kaiuz0nfferyx
    """
    SB = "sb"
    """Watch/band"""
    SD = "sd"
    """Robot vacuum

    https://developer.tuya.com/en/docs/iot/fsd?id=K9gf487ck1tlo
    """
    SF = "sf"
    """Sofa"""
    SGBJ = "sgbj"
    """Siren alarm

    https://developer.tuya.com/en/docs/iot/categorysgbj?id=Kaiuz37tlpbnu
    """
    SJ = "sj"
    """Water leak detector

    https://developer.tuya.com/en/docs/iot/categorysj?id=Kaiuz3iub2sli
    """
    SOS = "sos"
    """Emergency button

    https://developer.tuya.com/en/docs/iot/categorysos?id=Kaiuz3oi6agjy
    """
    SP = "sp"
    """Smart camera

    https://developer.tuya.com/en/docs/iot/categorysp?id=Kaiuz35leyo12
    """
    SZ = "sz"
    """Smart indoor garden

    https://developer.tuya.com/en/docs/iot/categorysz?id=Kaiuz4e6h7up0
    """
    TGKG = "tgkg"
    """Dimmer switch

    https://developer.tuya.com/en/docs/iot/categorytgkg?id=Kaiuz0ktx7m0o
    """
    TGQ = "tgq"
    """Dimmer

    https://developer.tuya.com/en/docs/iot/categorytgkg?id=Kaiuz0ktx7m0o
    """
    TNQ = "tnq"
    """Smart milk kettle"""
    TRACKER = "tracker"
    """Tracker"""
    TS = "ts"
    """Smart jump rope"""
    TYNDJ = "tyndj"
    """Solar light

    https://developer.tuya.com/en/docs/iot/tynd?id=Kaof8j02e1t98
    """
    TYY = "tyy"
    """Projector"""
    TZC1 = "tzc1"
    """Body fat scale"""
    VIDEOLOCK = "videolock"
    """Lock with camera"""
    WK = "wk"
    """Thermostat

    https://developer.tuya.com/en/docs/iot/f?id=K9gf45ld5l0t9
    """
    WSDCG = "wsdcg"
    """Temperature and humidity sensor

    https://developer.tuya.com/en/docs/iot/categorywsdcg?id=Kaiuz3hinij34
    """
    XDD = "xdd"
    """Ceiling light

    https://developer.tuya.com/en/docs/iot/ceiling-light?id=Kaiuz03xxfc4r
    """
    XFJ = "xfj"
    """Ventilation system"""
    XXJ = "xxj"
    """Diffuser

    https://developer.tuya.com/en/docs/iot/categoryxxj?id=Kaiuz1f9mo6bl
    """
    XY = "xy"
    """Washing machine"""
    YB = "yb"
    """Bathroom heater"""
    YG = "yg"
    """Bathtub"""
    YKQ = "ykq"
    """Remote control

    https://developer.tuya.com/en/docs/iot/ykq?id=Kaof8ljn81aov
    """
    YLCG = "ylcg"
    """Pressure sensor

    https://developer.tuya.com/en/docs/iot/categoryylcg?id=Kaiuz3kc2e4gm
    """
    YWBJ = "ywbj"
    """Smoke alarm

    https://developer.tuya.com/en/docs/iot/categoryywbj?id=Kaiuz3f6sf952
    """
    ZD = "zd"
    """Vibration sensor

    https://developer.tuya.com/en/docs/iot/categoryzd?id=Kaiuz3a5vrzno
    """
    ZNDB = "zndb"
    """Smart electricity meter

    https://developer.tuya.com/en/docs/iot/smart-meter?id=Kaiuz4gv6ack7
    """
    ZNFH = "znfh"
    """Bento box"""
    ZNSB = "znsb"
    """Smart water meter"""
    ZNYH = "znyh"
    """Smart pill box"""

    # Undocumented
    AQCZ = "aqcz"
    """Single Phase power meter (undocumented)"""
    BZYD = "bzyd"
    """White noise machine (undocumented)"""
    CWJWQ = "cwjwq"
    """Smart Odor Eliminator-Pro (undocumented)

    see https://github.com/orgs/home-assistant/discussions/79
    """
    DGHSXJ = "dghsxj"
    """Smart Camera - Low power consumption camera (undocumented)

    see https://github.com/home-assistant/core/issues/132844
    """
    DSD = "dsd"
    """Filament Light

    Based on data from https://github.com/home-assistant/core/issues/106703
    Product category mentioned in https://developer.tuya.com/en/docs/iot/oemapp-light?id=Kb77kja5woao6
    As at 30/12/23 not documented in https://developer.tuya.com/en/docs/iot/lighting?id=Kaiuyzxq30wmc
    """
    FSKG = "fskg"
    """Fan wall switch (undocumented)"""
    HJJCY = "hjjcy"
    """Air Quality Monitor

    https://developer.tuya.com/en/docs/iot/hjjcy?id=Kbeoad8y1nnlv
    """
    HXD = "hxd"
    """Wake Up Light II (undocumented)"""
    JDCLJQR = "jdcljqr"
    """Curtain Robot (undocumented)"""
    JQBJ = "jqbj"
    """Formaldehyde Detector (undocumented)"""
    KS = "ks"
    """Tower fan (undocumented)

    See https://github.com/orgs/home-assistant/discussions/329
    """
    MBD = "mbd"
    """Unknown light product

    Found as VECINO RGBW as provided by diagnostics
    """
    QCCDZ = "qccdz"
    """AC charging (undocumented)"""
    QJDCZ = "qjdcz"
    """ Unknown product with light capabilities

    Found in some diffusers, plugs and PIR flood lights
    """
    QXJ = "qxj"
    """Temperature and Humidity Sensor with External Probe (undocumented)

    see https://github.com/home-assistant/core/issues/136472
    """
    SFKZQ = "sfkzq"
    """Smart Water Timer (undocumented)"""
    SJZ = "sjz"
    """Electric desk (undocumented)"""
    SZJCY = "szjcy"
    """Water tester (undocumented)"""
    SZJQR = "szjqr"
    """Fingerbot (undocumented)"""
    SWTZ = "swtz"
    """Cooking thermometer (undocumented)"""
    TDQ = "tdq"
    """Dimmer (undocumented)"""
    TYD = "tyd"
    """Outdoor flood light (undocumented)"""
    VOC = "voc"
    """Volatile Organic Compound Sensor (undocumented)"""
    WG2 = "wg2"  # Documented, but not in official list
    """Gateway control

    https://developer.tuya.com/en/docs/iot/wg?id=Kbcdadk79ejok
    """
    WKCZ = "wkcz"
    """Two-way temperature and humidity switch (undocumented)

    "MOES Temperature and Humidity Smart Switch Module MS-103"
    """
    WKF = "wkf"
    """Thermostatic Radiator Valve (undocumented)"""
    WNYKQ = "wnykq"
    """Smart WiFi IR Remote (undocumented)

    eMylo Smart WiFi IR Remote
    Air Conditioner Mate (Smart IR Socket)
    """
    WXKG = "wxkg"  # Documented, but not in official list
    """Wireless Switch

    https://developer.tuya.com/en/docs/iot/s?id=Kbeoa9fkv6brp
    """
    XNYJCN = "xnyjcn"
    """Micro Storage Inverter

        Energy storage and solar PV inverter system with monitoring capabilities
    """
    YWCGQ = "ywcgq"
    """Tank Level Sensor (undocumented)"""
    ZNNBQ = "znnbq"
    """VESKA-micro inverter (undocumented)"""
    ZWJCY = "zwjcy"
    """Soil sensor - plant monitor (undocumented)"""
    ZNJXS = "znjxs"
    """Hejhome whitelabel Fingerbot (undocumented)"""
    ZNRB = "znrb"
    """Pool HeatPump (undocumented)"""

    DGNZK = "dgnzk"
    """Smart panel with switches and zigbee hub (undocumented) (localtuya extension)"""

    GCJ = "gcj"
    """EV Charger (undocumented) (localtuya extension)"""

    HDMIPMTBQ = "hdmipmtbq"
    """HDMI Sync Box A1 (undocumented) (localtuya extension)"""

    QT = "qt"
    """Generic products, EV Charger (undocumented) (localtuya extension)"""


class DPCode(StrEnum):
    """Data Point Codes used by Tuya.

    https://developer.tuya.com/en/docs/iot/standarddescription?id=K9i5ql6waswzq
    """

    A_CURRENT = "A_Current"
    A_VOLTAGE = "A_Voltage"
    AC_CURRENT = "ac_current"
    AC_VOLT = "ac_volt"
    ADD_ELE = "add_ele"
    ADD_ELE1 = "add_ele1"
    ADD_ELE2 = "add_ele2"
    AIR_QUALITY = "air_quality"
    AIR_QUALITY_INDEX = "air_quality_index"
    AIR_RETURN = "air_return"
    ALARM_DELAY_TIME = "alarm_delay_time"
    ALARM_LOCK = "alarm_lock"
    ALARM_MESSAGE = "alarm_message"
    ALARM_MSG = "alarm_msg"
    ALARM_RINGTONE = "alarm_ringtone"
    ALARM_SET_1 = "alarm_set_1"
    ALARM_SET_2 = "alarm_set_2"
    ALARM_SETTING = "alarm_setting"
    ALARM_STATE = "alarm_state"
    ALARM_SWITCH = "alarm_switch"
    ALARM_TIME = "alarm_time"
    ALARM_VOLUME = "alarm_volume"
    ALARMPERIOD = "AlarmPeriod"
    ALARMSWITCH = "AlarmSwitch"
    ALARMTYPE = "Alarmtype"
    ALL_ENERGY = "all_energy"
    AMBIEN = "ambien"  # codespell:ignore
    ANGLE_HORIZONTAL = "angle_horizontal"
    ANGLE_VERTICAL = "angle_vertical"
    ANION = "anion"
    ANTILOCK_STATUS = "antilock_status"
    APN = "apn"
    APN_USER_NAME = "apn_user_name"
    APN_USER_PASSWORD = "apn_user_password"
    APPOINTMENT_TIME = "appointment_time"
    ARM_DOWN_PERCENT = "arm_down_percent"
    ARM_UP_PERCENT = "arm_up_percent"
    ARMING_SWITCH = "arming_switch"
    ATMOSPHERIC_PRESSTURE = "atmospheric_pressture"
    AUTH_PASSWORD = "auth_password"
    AUTO_CLEAN = "auto_clean"
    AUTO_LOCK_TIME = "auto_lock_time"
    AUTOMATIC_LOCK = "automatic_lock"
    B_CURRENT = "B_Current"
    B_VOLTAGE = "B_Voltage"
    BACKLIGHT_SWITCH = "backlight_switch"
    BACKUP_RESERVE = "backup_reserve"
    BALANCE_ENERGY = "balance_energy"
    BASIC_ANTI_FLICKER = "basic_anti_flicker"
    BASIC_DEVICE_VOLUME = "basic_device_volume"
    BASIC_FLIP = "basic_flip"
    BASIC_INDICATOR = "basic_indicator"
    BASIC_NIGHTVISION = "basic_nightvision"
    BASIC_OSD = "basic_osd"
    BASIC_PRIVATE = "basic_private"
    BASIC_WDR = "basic_wdr"
    BASS_CONTROL = "bass_control"
    BATTERY = "battery"
    BATTERY_PERCENTAGE = "battery_percentage"
    BATTERY_POWER = "battery_power"
    BATTERY_STATE = "battery_state"
    BATTERY_VALUE = "battery_value"
    BATTERYSTATUS = "BatteryStatus"
    BEEP = "beep"
    BKLIGHT_SETTING = "bklight_setting"
    BOOLRESERVED01 = "boolreserved01"
    BOOLRESERVED02 = "boolreserved02"
    BOOLRESERVED03 = "boolreserved03"
    BREAK_CLEAN = "break_clean"
    BRIGHT_CONTROLLER = "bright_controller"
    BRIGHT_STATE = "bright_state"
    BRIGHT_VALUE = "bright_value"
    BRIGHT_VALUE_1 = "bright_value_1"
    BRIGHT_VALUE_2 = "bright_value_2"
    BRIGHT_VALUE_3 = "bright_value_3"
    BRIGHT_VALUE_4 = "bright_value_4"
    BRIGHT_VALUE_V2 = "bright_value_v2"
    BRIGHTNESS_MAX_1 = "brightness_max_1"
    BRIGHTNESS_MAX_2 = "brightness_max_2"
    BRIGHTNESS_MAX_3 = "brightness_max_3"
    BRIGHTNESS_MIN_1 = "brightness_min_1"
    BRIGHTNESS_MIN_2 = "brightness_min_2"
    BRIGHTNESS_MIN_3 = "brightness_min_3"
    C_CURRENT = "C_Current"
    C_F = "c_f"
    C_VOLTAGE = "C_Voltage"
    CALLPHONE = "callphone"
    CARD_BALANCE = "card_balance"
    CAT_WEIGHT = "cat_weight"
    CH2O_STATE = "ch2o_state"
    CH2O_VALUE = "ch2o_value"
    CH4_SENSOR_STATE = "ch4_sensor_state"
    CH4_SENSOR_VALUE = "ch4_sensor_value"
    CHARGE_CARD_NO1 = "charge_card_no1"
    CHARGE_CARD_NO2 = "charge_card_no2"
    CHARGE_ELECTRIC_QUANTITY = "charge_electric_quantity"
    CHARGE_ENERGY_ONCE = "charge_energy_once"
    CHARGE_MONEY = "charge_money"
    CHARGE_PATTERN = "charge_pattern"
    CHARGE_POWER1 = "charge_power1"
    CHARGE_POWER2 = "charge_power2"
    CHARGE_STATE = "charge_state"
    CHARGING_STATE = "charging_state"
    CHARGINGOPERATION = "ChargingOperation"
    CHILD_LOCK = "child_lock"
    CHILDLOCK = "childlock"
    CISTERN = "cistern"
    CLEAN = "clean"
    CLEAN_AREA = "clean_area"
    CLEAN_RECORD = "clean_record"
    CLEAN_TIME = "clean_time"
    CLEANING = "cleaning"
    CLEANING_NUM = "cleaning_num"
    CLEAR_ENERGY = "clear_energy"
    CLEARAPPOINTMENT = "ClearAppointment"
    CLICK_SUSTAIN_TIME = "click_sustain_time"
    CLOCK_SET = "clock_set"
    CLOSED_OPENED = "closed_opened"
    CLOSED_OPENED_KIT = "closed_opened_kit"
    CLOUD_RECIPE_NUMBER = "cloud_recipe_number"
    CO2_STATE = "co2_state"
    CO2_VALUE = "co2_value"
    CO_STATE = "co_state"
    CO_STATUS = "co_status"
    CO_VALUE = "co_value"
    COEF_B_RESET = "coef_b_reset"
    COIL_OUT = "coil_out"
    COLD_TEMP_CURRENT = "cold_temp_current"
    COLLECTION_MODE = "collection_mode"
    COLOR_DATA_V2 = "color_data_v2"
    COLOUR_DATA = "colour_data"
    COLOUR_DATA_HSV = "colour_data_hsv"
    COLOUR_DATA_RAW = "colour_data_raw"
    COLOUR_DATA_V2 = "colour_data_v2"
    COMPRESSOR_COMMAND = "compressor_command"
    COMPRESSOR_STRENGTH = "compressor_strength"
    CONCENTRATION_SET = "concentration_set"
    CONTROL = "control"
    CONTROL_2 = "control_2"
    CONTROL_3 = "control_3"
    CONTROL_4 = "control_4"
    CONTROL_BACK = "control_back"
    CONTROL_BACK_MODE = "control_back_mode"
    COOK_TEMPERATURE = "cook_temperature"
    COOK_TEMPERATURE_2 = "cook_temperature_2"
    COOK_TIME = "cook_time"
    COUNTDOWN = "countdown"
    COUNTDOWN_USB = "countdown"
    COUNTDOWN_1 = "countdown_1"
    COUNTDOWN_2 = "countdown_2"
    COUNTDOWN_3 = "countdown_3"
    COUNTDOWN_4 = "countdown_4"
    COUNTDOWN_5 = "countdown_5"
    COUNTDOWN_6 = "countdown_6"
    COUNTDOWN_7 = "countdown_7"
    COUNTDOWN_8 = "countdown_8"
    COUNTDOWN_LEFT = "countdown_left"
    COUNTDOWN_SET = "countdown_set"
    COUNTDOWN_USB1 = "countdown_usb1"
    COUNTDOWN_USB2 = "countdown_usb2"
    COUNTDOWN_USB3 = "countdown_usb3"
    COUNTDOWN_USB4 = "countdown_usb4"
    COUNTDOWN_USB5 = "countdown_usb5"
    COUNTDOWN_USB6 = "countdown_usb6"
    CP = "cp"
    CRUISE_MODE = "cruise_mode"
    CRY_DETECTION_SWITCH = "cry_detection_switch"
    CTIME = "Ctime"
    CUML_E_EXPORT_OFFGRID1 = "cuml_e_export_offgrid1"
    CUMULATIVE_ENERGY_CHARGED = "cumulative_energy_charged"
    CUMULATIVE_ENERGY_DISCHARGED = "cumulative_energy_discharged"
    CUMULATIVE_ENERGY_GENERATED_PV = "cumulative_energy_generated_pv"
    CUMULATIVE_ENERGY_OUTPUT_INV = "cumulative_energy_output_inv"
    CUP_NUMBER = "cup_number"
    CUR_CURRENT = "cur_current"
    CUR_CURRENT1 = "cur_current1"
    CUR_CURRENT2 = "cur_current2"
    CUR_NEUTRAL = "cur_neutral"
    CUR_POWER = "cur_power"
    CUR_POWER1 = "cur_power1"
    CUR_POWER2 = "cur_power2"
    CUR_VOLTAGE = "cur_voltage"
    CUR_VOLTAGE1 = "cur_voltage1"
    CUR_VOLTAGE2 = "cur_voltage2"
    CURRENT_A = "current_a"
    CURRENT_A_CALIBRATION = "current_a_calibration"
    CURRENT_B = "current_b"
    CURRENT_B_CALIBRATION = "current_b_calibration"
    CURRENT_C = "current_c"
    CURRENT_C_CALIBRATION = "current_c_calibration"
    CURRENT_SOC = "current_soc"
    DATA = "data"
    DATA_IDENTIFICATION = "data_identification"
    DATA_OVERFLOW = "data_overflow"
    DAY_ENERGY = "day_energy"
    DECIBEL_SENSITIVITY = "decibel_sensitivity"
    DECIBEL_SWITCH = "decibel_switch"
    DEFINEDIS = "definedis"
    DEFROST = "defrost"
    DEHUMIDITY_SET_ENUM = "dehumidify_set_enum"
    DEHUMIDITY_SET_VALUE = "dehumidify_set_value"
    DELAY_CLEAN_TIME = "delay_clean_time"
    DELAY_SET = "delay_set"
    DELAYDIS = "DelayDis"
    DEODORIZATION_NUM = "deodorization_num"
    DEVICE_NUMBER = "device_number"
    DEVICE_RESTART = "device_restart"
    DEVICE_STATE1 = "device_state1"
    DEVICE_STATE2 = "device_state2"
    DEVICEKW = "DeviceKw"
    DEVICEKWH = "DeviceKwh"
    DEVICEMAXSETA = "DeviceMaxSetA"
    DEVICESTATE = "DeviceState"
    DEVICETEMP = "DeviceTemp"
    DEVICETEMP2 = "DeviceTemp2"
    DEW_POINT_TEMP = "dew_point_temp"
    DIRECTION_A = "direction_a"
    DIRECTION_B = "direction_b"
    DIRECTION_C = "direction_c"
    DIRECTION_CONTROL = "direction_control"
    DIS_CURRENT = "dis_current"
    DISINFECTION = "disinfection"
    DM = "DM"
    DO_NOT_DISTURB = "do_not_disturb"
    DOOR_UNCLOSED = "door_unclosed"
    DOOR_UNCLOSED_TRIGGER = "door_unclosed_trigger"
    DOORBELL = "doorbell"
    DOORBELL_PIC = "doorbell_pic"
    DOORBELL_SONG = "doorbell_song"
    DOORCONTACT_STATE = "doorcontact_state"
    DOORCONTACT_STATE_2 = "doorcontact_state_2"
    DOORCONTACT_STATE_3 = "doorcontact_state_3"
    DOWN_CONFIRM = "down_confirm"
    DUSTER_CLOTH = "duster_cloth"
    EARTH_TEST = "earth_test"
    EC_CURRENT = "ec_current"
    ECO = "eco"
    ECO2 = "eco2"
    EDGE_BRUSH = "edge_brush"
    ELECTRICITY_LEFT = "electricity_left"
    ELECTRICITY_PHASE_A = "electricity_phase_a"
    ELECTRICITY_PHASE_B = "electricity_phase_b"
    ELECTRICITY_PHASE_C = "electricity_phase_c"
    ELECTRICITY_TOTAL = "electricity_total"
    EMISSION = "emission"
    EMPTY = "empty"
    ENERGY = "energy"
    ENERGY_A_CALIBRATION_FWD = "energy_a_calibration_fwd"
    ENERGY_A_CALIBRATION_REV = "energy_a_calibration_rev"
    ENERGY_B_CALIBRATION_FWD = "energy_b_calibration_fwd"
    ENERGY_B_CALIBRATION_REV = "energy_b_calibration_rev"
    ENERGY_C_CALIBRATION_FWD = "energy_c_calibration_fwd"
    ENERGY_C_CALIBRATION_REV = "energy_c_calibration_rev"
    ENERGY_FORWORD_A = "energy_forword_a"
    ENERGY_FORWORD_B = "energy_forword_b"
    ENERGY_FORWORD_C = "energy_forword_c"
    ENERGY_RESERSE_A = "energy_reserse_A"
    ENERGY_RESERSE_B = "energy_reserse_b"
    ENERGY_RESERSE_C = "energy_reserse_c"
    ENERGY_REVERSE_A = "energy_reverse_a"
    ENERGY_REVERSE_B = "energy_reverse_b"
    ENERGY_REVERSE_C = "energy_reverse_c"
    ENUMRESERVED01 = "enumreserved01"
    ENUMRESERVED02 = "enumreserved02"
    ENUMRESERVED03 = "enumreserved03"
    EQUIPMENT_TIME = "equipment_time"
    ERRO = "erro"  # codespell:ignore
    EXCRETION_TIME_DAY = "excretion_time_day"
    EXCRETION_TIMES_DAY = "excretion_times_day"
    EXT_TEMP = "ext_temp"
    FACTORY_RESET = "factory_reset"
    FAN_BEEP = "fan_beep"
    FAN_COOL = "fan_cool"
    FAN_COUNTDOWN = "fan_countdown"
    FAN_COUNTDOWN_2 = "fan_countdown_2"
    FAN_COUNTDOWN_3 = "fan_countdown_3"
    FAN_COUNTDOWN_4 = "fan_countdown_4"
    FAN_DIRECTION = "fan_direction"
    FAN_HORIZONTAL = "fan_horizontal"
    FAN_MODE = "fan_mode"
    FAN_SPEED = "fan_speed"
    FAN_SPEED_ENUM = "fan_speed_enum"
    FAN_SPEED_PERCENT = "fan_speed_percent"
    FAN_SWITCH = "fan_switch"
    FAN_VERTICAL = "fan_vertical"
    FAR_DETECTION = "far_detection"
    FAULT = "fault"
    FAULTRESERVED01 = "faultreserved01"
    FEED_REPORT = "feed_report"
    FEED_STATE = "feed_state"
    FEEDIN_POWER_LIMIT_ENABLE = "feedin_power_limit_enable"
    FEELLIKE_TEMP = "feellike_temp"
    FILTER = "filter"
    FILTER_LIFE = "filter"
    FILTER_DURATION = "filter_life"
    FILTER_RESET = "filter_reset"
    FLIGHT_BRIGHT_MODE = "flight_bright_mode"
    FLOODLIGHT_LIGHTNESS = "floodlight_lightness"
    FLOODLIGHT_SWITCH = "floodlight_switch"
    FLOW_SET = "flow_set"
    FORWARD_ENERGY_TOTAL = "forward_energy_total"
    FOUT_WAY_VALVE = "fout_way_valve"
    FREQ_CALIBRATION = "freq_calibration"
    FROST = "frost"
    GAS_SENSOR_STATE = "gas_sensor_state"
    GAS_SENSOR_STATUS = "gas_sensor_status"
    GAS_SENSOR_VALUE = "gas_sensor_value"
    HEAT_INDEX = "heat_index"
    HEAT_WD = "heat_wd"
    HIGHTPROTECTVALUE = "hightprotectvalue"
    HIJACK = "hijack"
    HISTORY = "History"
    HUM_ALARM = "hum_alarm"
    HUM_PERIODIC_REPORT = "hum_periodic_report"
    HUM_SENSITIVITY = "hum_sensitivity"
    HUMI_STATUS = "humi_status"
    HUMIDIFIER = "humidifier"
    HUMIDITY = "humidity"
    HUMIDITY_CURRENT = "humidity_current"
    HUMIDITY_INDOOR = "humidity_indoor"
    HUMIDITY_OUTDOOR = "humidity_outdoor"
    HUMIDITY_OUTDOOR_1 = "humidity_outdoor_1"
    HUMIDITY_OUTDOOR_2 = "humidity_outdoor_2"
    HUMIDITY_OUTDOOR_3 = "humidity_outdoor_3"
    HUMIDITY_SET = "humidity_set"
    HUMIDITY_VALUE = "humidity_value"
    IDU_ERROR = "idu_error"
    ILLUMINANCE_VALUE = "illuminance_value"
    INDICATOR_LIGHT = "indicator_light"
    INNERDRY = "innerdry"
    INSTALLATION_HEIGHT = "installation_height"
    INTERVAL_TIME = "interval_time"
    INVERTER_OUTPUT_POWER = "inverter_output_power"
    IPC_AUTO_SIREN = "ipc_auto_siren"
    IPC_BRIGHT = "ipc_bright"
    IPC_CONTRAST = "ipc_contrast"
    IPC_SHARP = "ipc_sharp"
    IPC_WORK_MODE = "ipc_work_mode"
    IR_SEND = "ir_send"
    IR_STUDY_CODE = "ir_study_code"
    IS_LOGIN = "is_login"
    KEY_STUDY = "key_study"
    KNOB_SWITCH_MODE_1 = "knob_switch_mode_1"
    LCD_ONOF = "lcd_onof"
    LED_TYPE_1 = "led_type_1"
    LED_TYPE_2 = "led_type_2"
    LED_TYPE_3 = "led_type_3"
    LEDLIGHT = "ledlight"
    LEVEL = "level"
    LEVEL_1 = "level_1"
    LEVEL_2 = "level_2"
    LEVEL_CURRENT = "level_current"
    LIGHT = "light"
    LIGHT_MODE = "light_mode"
    LIQUID_DEPTH = "liquid_depth"
    LIQUID_DEPTH_MAX = "liquid_depth_max"
    LIQUID_LEVEL_PERCENT = "liquid_level_percent"
    LIQUID_STATE = "liquid_state"
    LOAD_BALANCING_CURRENT = "load_balancing_current"
    LOAD_BALANCING_STATE = "load_balancing_state"
    LOADSTATUS = "loadstatus"
    LOCK = "lock"
    LOCK_MOTOR_STATE = "lock_motor_state"
    LOW_POWER_THRESHOLD = "low_power_threshold"
    LOWER_TEMP = "lower_temp"
    LOWER_TEMP_F = "lower_temp_f"
    LOWPROTECTVALUE = "lowprotectvalue"
    LUX = "lux"
    M_ADC_NUM = "M_ADC_NUM"
    MACH_OPERATE = "mach_operate"
    MACHINEAPPOINTMENT = "MachineAppointment"
    MACHINECONTROLCMD = "MachineControlCmd"
    MACHINECOVER = "MachineCover"
    MACHINEERROR = "MachineError"
    MACHINEERRORLOG = "MachineErrorLog"
    MACHINEPARTITION = "MachinePartition"
    MACHINEPASSWORD = "MachinePassword"
    MACHINERAINMODE = "MachineRainMode"
    MACHINESTATUS = "MachineStatus"
    MACHINEWARNING = "MachineWarning"
    MACHINEWORKLOG = "MachineWorkLog"
    MACHINEWORKTIME = "MachineWorktime"
    MAGNETNUM = "magnetNum"
    MANUAL_CLEAN = "manual_clean"
    MANUAL_FEED = "manual_feed"
    MASTER_MODE = "master_mode"
    MASTER_STATE = "master_state"
    MATERIAL = "material"
    MATERIAL_TYPE = "material_type"
    MAX_HUMI = "max_humi"
    MAX_SET = "max_set"
    MAXHUM_SET = "maxhum_set"
    MAXTEMP_SET = "maxtemp_set"
    MEAL_PLAN = "meal_plan"
    MEASUREMENT_MODEL = "measurement_model"
    MIDDLE_CONFIRM = "middle_confirm"
    MIN_HUMI = "min_humi"
    MINI_SET = "mini_set"
    MINIHUM_SET = "minihum_set"
    MINITEMP_SET = "minitemp_set"
    MOD = "mod"
    MOD_ON_TMR = "mod_on_tmr"
    MOD_ON_TMR_CD = "mod_on_tmr_cd"
    MODE = "mode"
    MODE_1 = "mode_1"
    MODE_2 = "mode_2"
    MODE_3 = "mode_3"
    MODE_4 = "mode_4"
    MODE_5 = "mode_5"
    MODE_6 = "mode_6"
    MOODLIGHTING = "moodlighting"
    MOTION_AREA_SWITCH = "motion_area_switch"
    MOTION_INTERVAL = "motion_interval"
    MOTION_RECORD = "motion_record"
    MOTION_SENSITIVITY = "motion_sensitivity"
    MOTION_SWITCH = "motion_switch"
    MOTION_TRACKING = "motion_tracking"
    MOTOR_MODE = "motor_mode"
    MOVEMENT_DETECT_PIC = "movement_detect_pic"
    MUFFLING = "muffling"
    MUTE = "mute"
    NEAR_DETECTION = "near_detection"
    NET_STATE = "net_state"
    NETWORK_MODEL = "network_model"
    NORMAL_OPEN_SWITCH = "normal_open_switch"
    NOTIFICATION_STATUS = "notification_status"
    OCPP_TLS = "ocpp_tls"
    OCPP_URL = "ocpp_url"
    ODU_FAN_SPEED = "odu_fan_speed"
    ONLINE_STATE = "online_state"
    OPEN_CLOSE = "open_close"
    OPPOSITE = "opposite"
    OPTIMUMSTART = "optimumstart"
    ORP_CURRENT = "orp_current"
    OTHEREVENT = "OtherEvent"
    OUT_POWER = "out_power"
    OUTPUT_POWER_LIMIT = "output_power_limit"
    OVERCHARGE_SWITCH = "overcharge_switch"
    OXYGEN = "oxygen"
    PAUSE = "pause"
    PEDAL_ANGLE = "pedal_angle"
    PEN_PROTECT = "pen_protect"
    PERCENT_CONTROL = "percent_control"
    PERCENT_CONTROL_2 = "percent_control_2"
    PERCENT_CONTROL_3 = "percent_control_3"
    PERCENT_CONTROL_4 = "percent_control_4"
    PERCENT_STATE = "percent_state"
    PERCENT_STATE_2 = "percent_state_2"
    PERCENT_STATE_3 = "percent_state_3"
    PERCENT_STATE_4 = "percent_state_4"
    PH_CURRENT = "ph_current"
    PHASE_A = "phase_a"
    PHASE_B = "phase_b"
    PHASE_C = "phase_c"
    PHASEFLAG = "PhaseFlag"
    PHOTO_MODE = "photo_mode"
    PILE_NUMBER = "pile_number"
    PIR = "pir"
    PIR_RADAR = "PIR_RADAR"
    PIR_SENSITIVITY = "pir_sensitivity"
    PIR_STATE = "pir_state"
    PIR_TIME = "pir_time"
    PLANT = "plant"
    PLAY_INFO = "play_info"
    PLAY_MODE = "play_mode"
    PLAY_TIME = "play_time"
    PM1 = "pm1"
    PM10 = "pm10"
    PM100_STATE = "pm100_state"
    PM100_VALUE = "pm100_value"
    PM10_STATE = "pm10_state"
    PM10_VALUE = "pm10_value"
    PM25 = "pm25"
    PM25_STATE = "pm25_state"
    PM25_VALUE = "pm25_value"
    POSITION = "position"
    POWDER_SET = "powder_set"
    POWER = "power"
    POWER_A = "power_a"
    POWER_A_CALIBRATION = "power_a_calibration"
    POWER_ADJUSTMENT = "power_adjustmen"
    POWER_B = "power_b"
    POWER_B_CALIBRATION = "power_b_calibration"
    POWER_C = "power_c"
    POWER_C_CALIBRATION = "power_c_calibration"
    POWER_FACTOR = "power_factor"
    POWER_FACTOR_A = "power_factor_a"
    POWER_FACTOR_B = "power_factor_b"
    POWER_FACTOR_C = "power_factor_c"
    POWER_GO = "power_go"
    POWER_TOTAL = "power_total"
    POWER_TYPE = "power_type"
    POWER_TYPE1 = "power_type1"
    POWER_TYPE2 = "power_type2"
    POWEREVENT = "PowerEvent"
    PREHEAT = "preheat"
    PREHEAT_1 = "preheat_1"
    PREHEAT_2 = "preheat_2"
    PRESENCE_STATE = "presence_state"
    PRESSURE_STATE = "pressure_state"
    PRESSURE_UNIT_CONVERT = "pressure_unit_convert"
    PRESSURE_VALUE = "pressure_value"
    PRM_CONTENT = "prm_content"
    PRM_TEMPERATURE = "prm_temperature"
    PRO_ADD_ELE = "pro_add_ele"
    PTZ_CONTROL = "ptz_control"
    PTZ_STOP = "ptz_stop"
    PUMP = "pump"
    PUMP_RESET = "pump_reset"
    PUMP_TIME = "pump_time"
    PV_CURRENT = "pv_current"
    PV_POWER = "pv_power"
    PV_POWER_CHANNEL_1 = "pv_power_channel_1"
    PV_POWER_CHANNEL_2 = "pv_power_channel_2"
    PV_POWER_TOTAL = "pv_power_total"
    PV_VOLT = "pv_volt"
    PVRPM = "pvrpm"
    QR_CODE_PREFIX = "qr_code_prefix"
    QUERYAPPOINTMENT = "QueryAppointment"
    QUERYPARTITION = "QueryPartition"
    QUICK_FEED = "quick_feed"
    QUIET_TIME_END = "quiet_time_end"
    QUIET_TIME_START = "quiet_time_start"
    QUIET_TIMING_ON = "quiet_timing_on"
    RAIN_24H = "rain_24h"
    RAIN_RATE = "rain_rate"
    RATED_CURRENT = "rated_current"
    RAWRESERVED01 = "rawreserved01"
    RAWRESERVED02 = "rawreserved02"
    RAWRESERVED03 = "rawreserved03"
    REBOOT = "reboot"
    RECORD_MODE = "record_mode"
    RECORD_SWITCH = "record_switch"
    RELAY_STATUS = "relay_status"
    RELAY_STATUS_1 = "relay_status_1"
    RELAY_STATUS_2 = "relay_status_2"
    RELAY_STATUS_3 = "relay_status_3"
    RELAY_STATUS_4 = "relay_status_4"
    RELAY_STATUS_5 = "relay_status_5"
    RELAY_STATUS_6 = "relay_status_6"
    RELAY_STATUS_7 = "relay_status_7"
    RELAY_STATUS_8 = "relay_status_8"
    REMAIN_TIME = "remain_time"
    REMOTE_REGISTER = "remote_register"
    REMOTE_UNLOCK_SWITCH = "remote_unlock_switch"
    REPORT_PERIOD_SET = "report_period_set"
    REPORT_RATE_CONTROL = "report_rate_control"
    RESET_DUSTER_CLOTH = "reset_duster_cloth"
    RESET_EDGE_BRUSH = "reset_edge_brush"
    RESET_FILTER = "reset_filter"
    RESET_LIMIT = "reset_limit"
    RESET_MAP = "reset_map"
    RESET_ROLL_BRUSH = "reset_roll_brush"
    RESIDUAL_ELECTRICITY = "residual_electricity"
    REVERSE_ENERGY_TOTAL = "reverse_energy_total"
    RFID = "RFID"
    ROLL_BRUSH = "roll_brush"
    RUNNING_FAN_SPEED = "running_fan_speed"
    SCENE_1 = "scene_1"
    SCENE_10 = "scene_10"
    SCENE_11 = "scene_11"
    SCENE_12 = "scene_12"
    SCENE_13 = "scene_13"
    SCENE_14 = "scene_14"
    SCENE_15 = "scene_15"
    SCENE_16 = "scene_16"
    SCENE_17 = "scene_17"
    SCENE_18 = "scene_18"
    SCENE_19 = "scene_19"
    SCENE_2 = "scene_2"
    SCENE_20 = "scene_20"
    SCENE_3 = "scene_3"
    SCENE_4 = "scene_4"
    SCENE_5 = "scene_5"
    SCENE_6 = "scene_6"
    SCENE_7 = "scene_7"
    SCENE_8 = "scene_8"
    SCENE_9 = "scene_9"
    SCENE_DATA = "scene_data"
    SCENE_DATA_RAW = "scene_data_raw"
    SCENE_DATA_V2 = "scene_data_v2"
    SEEK = "seek"
    SENS = "sens"
    SENSITIVITY = "sensitivity"
    SENSOR_HUMIDITY = "sensor_humidity"
    SENSOR_LINE = "sensor_line"
    SENSOR_TEMPERATURE = "sensor_temperature"
    SENSORTYPE = "sensortype"
    SET16A = "Set16A"
    SET32A = "Set32A"
    SET40A = "Set40A"
    SET50A = "Set50A"
    SET60A = "set60a"
    SET80A = "set80a"
    SETDEFINETIME = "SetDefineTime"
    SETDELAYTIME = "SetDelayTime"
    SETTING = "setting"
    SHAKE = "shake"
    SHOCK_STATE = "shock_state"
    SIREN_SWITCH = "siren_switch"
    SITUATION_SET = "situation_set"
    SLEEP = "sleep"
    SLEEPING = "sleeping"
    SLOW_FEED = "slow_feed"
    SMART_WEATHER = "smart_weather"
    SMOKE_SENSOR_STATE = "smoke_sensor_state"
    SMOKE_SENSOR_STATUS = "smoke_sensor_status"
    SMOKE_SENSOR_VALUE = "smoke_sensor_value"
    SNOOZE = "snooze"
    SOS = "sos"
    SOS_STATE = "sos_state"
    SOUND_EFFECTS = "sound_effects"
    SOUND_MODE = "sound_mode"
    SOURCE = "source"
    SPEED = "speed"
    SPEEK = "speek"
    SPRAY_MODE = "spray_mode"
    SPRAY_VOLUME = "spray_volume"
    STA = "sta"
    START = "start"
    STATUS = "status"
    STERILIZATION = "sterilization"
    STRIP_DIRECTION = "strip_direction"
    STRIP_INPUT_POS = "strip_input_pos"
    STRRESERVED01 = "strreserved01"
    STRRESERVED02 = "strreserved02"
    STRRESERVED03 = "strreserved03"
    STUDY_CODE = "study_code"
    SUB_CLASS = "sub_class"
    SUB_STATE = "sub_state"
    SUB_TYPE = "sub_type"
    SUCTION = "suction"
    SUPPLY_FREQUENCY = "supply_frequency"
    SWING = "swing"
    SWITCH = "switch"
    SWITCH1 = "switch1"
    SWITCH1_VALUE = "switch1_value"
    SWITCH2 = "switch2"
    SWITCH2_VALUE = "switch2_value"
    SWITCH3 = "switch3"
    SWITCH3_VALUE = "switch3_value"
    SWITCH4 = "switch4"
    SWITCH4_VALUE = "switch4_value"
    SWITCH5 = "switch5"
    SWITCH5_VALUE = "switch5_value"
    SWITCH6 = "switch6"
    SWITCH6_VALUE = "switch6_value"
    SWITCH7 = "switch7"
    SWITCH8 = "switch8"
    SWITCH_1 = "switch_1"
    SWITCH_2 = "switch_2"
    SWITCH_3 = "switch_3"
    SWITCH_4 = "switch_4"
    SWITCH_5 = "switch_5"
    SWITCH_6 = "switch_6"
    SWITCH_7 = "switch_7"
    SWITCH_8 = "switch_8"
    SWITCH_ALARM_CALL = "switch_alarm_call"
    SWITCH_ALARM_LIGHT = "switch_alarm_light"
    SWITCH_ALARM_PROPEL = "switch_alarm_propel"
    SWITCH_ALARM_SMS = "switch_alarm_sms"
    SWITCH_ALARM_SOUND = "switch_alarm_sound"
    SWITCH_BACKLIGHT = "switch_backlight"
    SWITCH_CHARGE = "switch_charge"
    SWITCH_COLD = "switch_cold"
    SWITCH_CONTROLLER = "switch_controller"
    SWITCH_DISTURB = "switch_disturb"
    SWITCH_FAN = "switch_fan"
    SWITCH_HORIZONTAL = "switch_horizontal"
    SWITCH_KB_LIGHT = "switch_kb_light"
    SWITCH_KB_SOUND = "switch_kb_sound"
    SWITCH_LED = "switch_led"
    SWITCH_LED_1 = "switch_led_1"
    SWITCH_LED_2 = "switch_led_2"
    SWITCH_LED_3 = "switch_led_3"
    SWITCH_LED_4 = "switch_led_4"
    SWITCH_MODE1 = "switch_mode1"
    SWITCH_MODE2 = "switch_mode2"
    SWITCH_MODE3 = "switch_mode3"
    SWITCH_MODE4 = "switch_mode4"
    SWITCH_MODE5 = "switch_mode5"
    SWITCH_MODE6 = "switch_mode6"
    SWITCH_MODE7 = "switch_mode7"
    SWITCH_MODE8 = "switch_mode8"
    SWITCH_MODE9 = "switch_mode9"
    SWITCH_MUSIC = "switch_music"
    SWITCH_NIGHT_LIGHT = "switch_night_light"
    SWITCH_SAVE_ENERGY = "switch_save_energy"
    SWITCH_SOUND = "switch_sound"
    SWITCH_SPRAY = "switch_spray"
    SWITCH_STOP = "switch_stop"
    SWITCH_TYPE_1 = "switch_type_1"
    SWITCH_TYPE_2 = "switch_type_2"
    SWITCH_TYPE_3 = "switch_type_3"
    SWITCH_TYPE_4 = "switch_type_4"
    SWITCH_TYPE_5 = "switch_type_5"
    SWITCH_USB1 = "switch_usb1"
    SWITCH_USB2 = "switch_usb2"
    SWITCH_USB3 = "switch_usb3"
    SWITCH_USB4 = "switch_usb4"
    SWITCH_USB5 = "switch_usb5"
    SWITCH_USB6 = "switch_usb6"
    SWITCH_VERTICAL = "switch_vertical"
    SWITCH_VOICE = "switch_voice"
    SWITCH_WEATHER = "switch_weather"
    SWITCH_WELCOME = "switch_welcome"
    SYNC_REQUEST = "sync_request"
    SYNC_RESPONSE = "sync_response"
    SYSTEM_VERSION = "system_version"
    SYSTEMMODE = "systemmode"
    TARGET_DIS_CLOSEST = "target_dis_closest"
    TBD = "tbd"
    TDS_IN = "tds_in"
    TEMP = "temp"
    TEMP_ADC = "temp_adc"
    TEMP_ALARM = "temp_alarm"
    TEMP_AROUND = "temp_around"
    TEMP_BOILING_C = "temp_boiling_c"
    TEMP_BOILING_F = "temp_boiling_f"
    TEMP_COILER = "temp_coiler"
    TEMP_CONTROLLER = "temp_controller"
    TEMP_CORRECTION = "temp_correction"
    TEMP_CURRENT = "temp_current"
    TEMP_CURRENT_2 = "temp_current_2"
    TEMP_CURRENT_EXTERNAL = "temp_current_external"
    TEMP_CURRENT_EXTERNAL_1 = "temp_current_external_1"
    TEMP_CURRENT_EXTERNAL_2 = "temp_current_external_2"
    TEMP_CURRENT_EXTERNAL_3 = "temp_current_external_3"
    TEMP_CURRENT_EXTERNAL_F = "temp_current_external_f"
    TEMP_CURRENT_F = "temp_current_f"
    TEMP_EFFLUENT = "temp_effluent"
    TEMP_INDOOR = "temp_indoor"
    TEMP_LOW = "temp_low"
    TEMP_PERIODIC_REPORT = "temp_periodic_report"
    TEMP_SENSITIVITY = "temp_sensitivity"
    TEMP_SET = "temp_set"
    TEMP_SET_F = "temp_set_f"
    TEMP_SETTING_QUICK_C = "temp_setting_quick_c"
    TEMP_STATUS = "temp_status"
    TEMP_UNIT_CONVERT = "temp_unit_convert"
    TEMP_UP = "temp_up"
    TEMP_VALUE = "temp_value"
    TEMP_VALUE_V2 = "temp_value_v2"
    TEMP_VENTING = "temp_venting"
    TEMPACTIVATE = "tempactivate"
    TEMPCOMP = "tempcomp"
    TEMPCURRENT = "tempcurrent"
    TEMPER_ALARM = "temper_alarm"
    TEMPERATURE = "temperature"
    TEMPFLOOR = "TempFloor"
    TEMPPROGRAM = "tempprogram"
    TEST = "test"
    TIM = "tim"
    TIME_FORMAT = "Time_Format"
    TIME_TOTAL = "time_total"
    TIME_USE = "time_use"
    TIMER = "timer"
    TODAY_ACC_ENERGY = "today_acc_energy"
    TODAY_ACC_ENERGY1 = "today_acc_energy1"
    TODAY_ACC_ENERGY2 = "today_acc_energy2"
    TODAY_ENERGY_ADD = "today_energy_add"
    TODAY_ENERGY_ADD1 = "today_energy_add1"
    TODAY_ENERGY_ADD2 = "today_energy_add2"
    TOTAL_CLEAN_AREA = "total_clean_area"
    TOTAL_CLEAN_COUNT = "total_clean_count"
    TOTAL_CLEAN_TIME = "total_clean_time"
    TOTAL_ENERGY = "total_energy"
    TOTAL_ENERGY1 = "total_energy1"
    TOTAL_ENERGY2 = "total_energy2"
    TOTAL_FORWARD_ENERGY = "total_forward_energy"
    TOTAL_PM = "total_pm"
    TOTAL_POWER = "total_power"
    TOTAL_TIME = "total_time"
    TOUCH_WARNING = "touch_warning"
    TRANSACTION_ENERGY = "transaction_energy"
    TRANSACTION_MONRY = "transaction_monry"
    TRANSACTION_STATUS = "transaction_status"
    TRANSACTION_TIME = "transaction_time"
    TRASH_STATUS = "trash_status"
    TREBLE_CONTROL = "treble_control"
    TV_SIZE = "tv_size"
    TVOC = "tvoc"
    UID = "UID"
    UNLOCK_APP = "unlock_app"
    UNLOCK_BLE = "unlock_ble"
    UNLOCK_CARD = "unlock_card"
    UNLOCK_DOUBLE = "unlock_double"
    UNLOCK_DYNAMIC = "unlock_dynamic"
    UNLOCK_EYE = "unlock_eye"
    UNLOCK_FACE = "unlock_face"
    UNLOCK_FINGER_VEIN = "unlock_finger_vein"
    UNLOCK_FINGERPRINT = "unlock_fingerprint"
    UNLOCK_HAND = "unlock_hand"
    UNLOCK_IDENTITY_CARD = "unlock_identity_card"
    UNLOCK_KEY = "unlock_key"
    UNLOCK_PASSWORD = "unlock_password"
    UNLOCK_PHONE_REMOTE = "unlock_phone_remote"
    UNLOCK_REMOTE = "unlock_remote"
    UNLOCK_REQUEST = "unlock_request"
    UNLOCK_SPECIAL = "unlock_special"
    UNLOCK_SWITCH = "unlock_switch"
    UNLOCK_TEMPORARY = "unlock_temporary"
    UNLOCK_VOICE_REMOTE = "unlock_voice_remote"
    UP_CONFIRM = "up_confirm"
    UP_DOWN = "up_down"
    UPDATE_PASSWORD = "update_password"
    UPPER_TEMP = "upper_temp"
    UPPER_TEMP_F = "upper_temp_f"
    USB_BZ = "usb_bz"
    USE_TIME = "use_time"
    USE_TIME_ONE = "use_time_one"
    UV = "uv"
    UV_INDEX = "uv_index"
    UV_RUNTIME = "uv_runtime"
    VA_BATTERY = "va_battery"
    VA_HUMIDITY = "va_humidity"
    VA_TEMPERATURE = "va_temperature"
    VALUERESERVED01 = "valuereserved01"
    VALUERESERVED02 = "valuereserved02"
    VALUERESERVED03 = "valuereserved03"
    VALVE_STATE = "valve_state"
    VERSION_NUMBER = "version_number"
    VIDEO_INTENSITY = "video_intensity"
    VIDEO_MODE = "video_mode"
    VIDEO_SCENE = "video_scene"
    VOC_STATE = "voc_state"
    VOC_VALUE = "voc_value"
    VOICE_BT_PLAY = "voice_bt_play"
    VOICE_LANGUAGE = "voice_language"
    VOICE_MIC = "voice_mic"
    VOICE_PLAY = "voice_play"
    VOICE_SWITCH = "voice_switch"
    VOICE_TIMES = "voice_times"
    VOICE_VOL = "voice_vol"
    VOLTAGE_A = "voltage_a"
    VOLTAGE_COEF = "voltage_coef"
    VOLTAGE_CURRENT = "voltage_current"
    VOLTAGE_PHASE_A = "voltage_phase_a"
    VOLTAGE_PHASE_B = "voltage_phase_b"
    VOLTAGE_PHASE_C = "voltage_phase_c"
    VOLUME_SET = "volume_set"
    WARM = "warm"
    WARM_TIME = "warm_time"
    WARN_POWER = "warn_power"
    WARN_POWER1 = "warn_power1"
    WARN_POWER2 = "warn_power2"
    WATER = "water"
    WATER_LEVEL = "water_level"
    WATER_RESET = "water_reset"
    WATER_SET = "water_set"
    WATER_TEMP = "water_temp"
    WATER_TIME = "water_time"
    WATER_USE_DATA = "water_use_data"
    WATERSENSOR_STATE = "watersensor_state"
    WEATHER_DELAY = "weather_delay"
    WET = "wet"
    WIND_DIRECT = "wind_direct"
    WINDCHILL_INDEX = "windchill_index"
    WINDOW_CHECK = "window_check"
    WINDOW_STATE = "window_state"
    WINDOWDETECT = "windowdetect"
    WINDSPEED = "windspeed"
    WINDSPEED_AVG = "windspeed_avg"
    WINDSPEED_UNIT_CONVERT = "windspeed_unit_convert"
    WIRELESS_BATTERYLOCK = "wireless_batterylock"
    WIRELESS_ELECTRICITY = "wireless_electricity"
    WORK_MODE = "work_mode"
    WORK_POWER = "work_power"
    WORK_STAT = "work_stat"
    WORK_STATE = "work_state"
    WORK_STATE_E = "work_state_e"
    WORK_STATUS = "work_status"
    WORK_TYPE = "work_type"
    Y_MOP = "y_mop"
    ZONE_ATTRIBUTE = "zone_attribute"
    ZONE_NUMBER = "zone_number"
