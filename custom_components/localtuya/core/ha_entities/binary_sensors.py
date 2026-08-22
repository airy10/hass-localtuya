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
from homeassistant.components.binary_sensor import BinarySensorDeviceClass

CONF_STATE_ON = "state_on"

ALARM_ON = {CONF_STATE_ON: "alarm"}
STATE_TRUE = {CONF_STATE_ON: "true"}
ON_1 = {CONF_STATE_ON: "1"}
ON_FEEDING = {CONF_STATE_ON: "feeding"}
ON_PRESENCE = {CONF_STATE_ON: "presence"}

ON_OPEN = {CONF_STATE_ON: "open"}
ON_OPENED = {CONF_STATE_ON: "opened"}

ON_AQAB = {CONF_STATE_ON: "AQAB"}


def localtuya_binarySensor(state_on="1"):
    """Define localtuya binary_sensor configs"""
    data = {CONF_STATE_ON: state_on}
    return data


# Commonly used sensors
TAMPER_BINARY_SENSOR = LocalTuyaEntity(
    key=DPCode.TEMPER_ALARM,
    name="Tamper",
    device_class=BinarySensorDeviceClass.TAMPER,
    entity_category=EntityCategory.DIAGNOSTIC,
    custom_configs=STATE_TRUE,
)

# Fault
FAULT_SENSOR = (
    LocalTuyaEntity(
        id=DPCode.FAULT,
        name="Fault",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        custom_configs=ON_1,
    ),
    LocalTuyaEntity(
        id=DPCode.MACHINEERROR,
        name="Fault",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        custom_configs=ON_1,
    ),
    LocalTuyaEntity(
        id=DPCode.IDU_ERROR,
        name="IDU Error",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        custom_configs=ON_1,
    ),
    # CZ - Energy monitor?
    LocalTuyaEntity(
        id=DPCode.POWER_TYPE,
        name="Power State",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        custom_configs=localtuya_binarySensor("warn"),
    ),
    LocalTuyaEntity(
        id=DPCode.POWER_TYPE1,
        name="Power 1 State",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        custom_configs=localtuya_binarySensor("warn"),
    ),
    LocalTuyaEntity(
        id=DPCode.POWER_TYPE2,
        name="Power 2 State",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        custom_configs=localtuya_binarySensor("warn"),
    ),
)


BINARY_SENSORS: dict[DeviceCategory, tuple[LocalTuyaEntity, ...]] = {
    # Fan
    # https://developer.tuya.com/en/docs/iot/categoryfs?id=Kaiuz1xweel1c
    DeviceCategory.FS: (
        LocalTuyaEntity(
            id=DPCode.ERRO,  # codespell:ignore
            name="Error",
            device_class=BinarySensorDeviceClass.PROBLEM,
            entity_category=EntityCategory.DIAGNOSTIC,
            custom_configs=ON_1,
        ),
        LocalTuyaEntity(
            id=DPCode.USB_BZ,
            name="USB",
            device_class=BinarySensorDeviceClass.PLUG,
            entity_category=EntityCategory.DIAGNOSTIC,
            custom_configs=STATE_TRUE,
        ),
    ),
    # Multi-functional Sensor
    # https://developer.tuya.com/en/docs/iot/categorydgnbj?id=Kaiuz3yorvzg3
    DeviceCategory.DGNBJ: (
        LocalTuyaEntity(
            id=DPCode.GAS_SENSOR_STATE,
            name="Gas detection",
            icon="mdi:gas-cylinder",
            device_class=BinarySensorDeviceClass.GAS,
            custom_configs=ALARM_ON,
        ),
        LocalTuyaEntity(
            id=DPCode.CH4_SENSOR_STATE,
            name="Methane detection",
            device_class=BinarySensorDeviceClass.GAS,
            custom_configs=ALARM_ON,
        ),
        LocalTuyaEntity(
            id=DPCode.VOC_STATE,
            name="VOC detection",
            device_class=BinarySensorDeviceClass.SAFETY,
            custom_configs=ALARM_ON,
        ),
        LocalTuyaEntity(
            id=DPCode.PM10_STATE,
            name="PM1.0 detection",
            device_class=BinarySensorDeviceClass.SAFETY,
            custom_configs=ALARM_ON,
        ),
        LocalTuyaEntity(
            id=DPCode.PM25_STATE,
            name="PM2.5 detection",
            device_class=BinarySensorDeviceClass.SAFETY,
            custom_configs=ALARM_ON,
        ),
        LocalTuyaEntity(
            id=DPCode.PM100_STATE,
            name="PM10 detection",
            device_class=BinarySensorDeviceClass.SAFETY,
            custom_configs=ALARM_ON,
        ),
        LocalTuyaEntity(
            id=DPCode.CO_STATE,
            name="CO detection",
            icon="mdi:molecule-co",
            device_class=BinarySensorDeviceClass.SAFETY,
            custom_configs=ALARM_ON,
        ),
        LocalTuyaEntity(
            id=DPCode.CO2_STATE,
            name="CO2 detection",
            icon="mdi:molecule-co2",
            device_class=BinarySensorDeviceClass.SAFETY,
            custom_configs=ALARM_ON,
        ),
        LocalTuyaEntity(
            id=DPCode.CH2O_STATE,
            name="Formaldehyde detection",
            device_class=BinarySensorDeviceClass.SAFETY,
            custom_configs=ALARM_ON,
        ),
        LocalTuyaEntity(
            id=DPCode.DOORCONTACT_STATE,
            name="Door",
            device_class=BinarySensorDeviceClass.DOOR,
            custom_configs=STATE_TRUE,
        ),
        LocalTuyaEntity(
            id=DPCode.WATERSENSOR_STATE,
            device_class=BinarySensorDeviceClass.MOISTURE,
            custom_configs=ALARM_ON,
        ),
        LocalTuyaEntity(
            id=DPCode.PRESSURE_STATE,
            name="Pressure",
            custom_configs=ALARM_ON,
        ),
        LocalTuyaEntity(
            id=DPCode.SMOKE_SENSOR_STATE,
            name="Smoke detection",
            icon="mdi:smoke-detector",
            device_class=BinarySensorDeviceClass.SMOKE,
            custom_configs=ALARM_ON,
        ),
        TAMPER_BINARY_SENSOR,
    ),
    # CO2 Detector
    # https://developer.tuya.com/en/docs/iot/categoryco2bj?id=Kaiuz3wes7yuy
    DeviceCategory.CO2BJ: (
        LocalTuyaEntity(
            id=DPCode.CO2_STATE,
            icon="mdi:molecule-co2",
            device_class=BinarySensorDeviceClass.SAFETY,
            custom_configs=ALARM_ON,
        ),
        TAMPER_BINARY_SENSOR,
    ),
    # CO Detector
    # https://developer.tuya.com/en/docs/iot/categorycobj?id=Kaiuz3u1j6q1v
    DeviceCategory.COBJ: (
        LocalTuyaEntity(
            id=DPCode.CO_STATE,
            icon="mdi:molecule-co",
            device_class=BinarySensorDeviceClass.SAFETY,
            custom_configs=ON_1,
        ),
        LocalTuyaEntity(
            id=DPCode.CO_STATUS,
            icon="mdi:molecule-co",
            device_class=BinarySensorDeviceClass.SAFETY,
            custom_configs=ALARM_ON,
        ),
        TAMPER_BINARY_SENSOR,
    ),
    # Smart Pet Feeder
    # https://developer.tuya.com/en/docs/iot/categorycwwsq?id=Kaiuz2b6vydld
    DeviceCategory.CWWSQ: (
        LocalTuyaEntity(
            id=DPCode.FEED_STATE,
            icon="mdi:information",
            custom_configs=ON_FEEDING,
        ),
        LocalTuyaEntity(
            id=DPCode.CHARGE_STATE,
            device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
            entity_category=EntityCategory.DIAGNOSTIC,
            custom_configs=STATE_TRUE,
        ),
        *FAULT_SENSOR,
    ),
    # Human Presence Sensor
    # https://developer.tuya.com/en/docs/iot/categoryhps?id=Kaiuz42yhn1hs
    DeviceCategory.HPS: (
        LocalTuyaEntity(
            id=DPCode.PRESENCE_STATE,
            device_class=BinarySensorDeviceClass.MOTION,
            custom_configs=ON_PRESENCE,
        ),
    ),
    # Formaldehyde Detector
    # Note: Not documented
    DeviceCategory.JQBJ: (
        LocalTuyaEntity(
            id=DPCode.CH2O_STATE,
            device_class=BinarySensorDeviceClass.SAFETY,
            custom_configs=ALARM_ON,
        ),
        TAMPER_BINARY_SENSOR,
    ),
    # Methane Detector
    # https://developer.tuya.com/en/docs/iot/categoryjwbj?id=Kaiuz40u98lkm
    DeviceCategory.JWBJ: (
        LocalTuyaEntity(
            id=DPCode.CH4_SENSOR_STATE,
            device_class=BinarySensorDeviceClass.GAS,
            custom_configs=ALARM_ON,
        ),
        TAMPER_BINARY_SENSOR,
    ),
    # Door and Window Controller
    # https://developer.tuya.com/en/docs/iot/s?id=K9gf48r5zjsy9
    DeviceCategory.MC: (
        LocalTuyaEntity(
            id=DPCode.STATUS,
            device_class=BinarySensorDeviceClass.DOOR,
            custom_configs=ON_OPENED,
        ),
        LocalTuyaEntity(
            id=DPCode.DOOR_UNCLOSED,
            device_class=BinarySensorDeviceClass.DOOR,
            custom_configs=STATE_TRUE,
        ),
    ),
    # Cat litter box
    # https://developer.tuya.com/en/docs/iot/f?id=Kakg309qkmuit
    DeviceCategory.MSP: (
        LocalTuyaEntity(
            id=DPCode.CLEANING_NUM,
            name="Cleaning",
            custom_configs=STATE_TRUE,
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        LocalTuyaEntity(
            id=DPCode.NOTIFICATION_STATUS,
            name="Notification",
            custom_configs=STATE_TRUE,
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        LocalTuyaEntity(
            id=DPCode.TRASH_STATUS,
            name="Trash",
            custom_configs=STATE_TRUE,
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        LocalTuyaEntity(
            id=DPCode.POWER,
            name="Power",
            device_class=BinarySensorDeviceClass.POWER,
            custom_configs=STATE_TRUE,
        ),
        *FAULT_SENSOR,
    ),
    # Door Window Sensor
    # https://developer.tuya.com/en/docs/iot/s?id=K9gf48hm02l8m
    DeviceCategory.MCS: (
        LocalTuyaEntity(
            id=DPCode.DOORCONTACT_STATE,
            device_class=BinarySensorDeviceClass.DOOR,
            custom_configs=STATE_TRUE,
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH,  # Used by non-standard contact sensor implementations
            device_class=BinarySensorDeviceClass.DOOR,
            custom_configs=STATE_TRUE,
        ),
        TAMPER_BINARY_SENSOR,
    ),
    # Access Control
    # https://developer.tuya.com/en/docs/iot/s?id=Kb0o2xhlkxbet
    DeviceCategory.MK: (
        LocalTuyaEntity(
            id=DPCode.CLOSED_OPENED_KIT,
            device_class=BinarySensorDeviceClass.LOCK,
            custom_configs=ON_AQAB,
        ),
    ),
    # Access Control
    # https://developer.tuya.com/en/docs/iot/s?id=Kb0o2xhlkxbet
    DeviceCategory.MK: (
        LocalTuyaEntity(
            id=DPCode.CLOSED_OPENED_KIT,
            device_class=BinarySensorDeviceClass.LOCK,
            custom_configs=ON_AQAB,
        ),
    ),
    # Luminance Sensor
    # https://developer.tuya.com/en/docs/iot/categoryldcg?id=Kaiuz3n7u69l8
    DeviceCategory.LDCG: (
        LocalTuyaEntity(
            id=DPCode.TEMPER_ALARM,
            device_class=BinarySensorDeviceClass.TAMPER,
            entity_category=EntityCategory.DIAGNOSTIC,
            custom_configs=STATE_TRUE,
        ),
        TAMPER_BINARY_SENSOR,
    ),
    # PIR Detector
    # https://developer.tuya.com/en/docs/iot/categorypir?id=Kaiuz3ss11b80
    DeviceCategory.PIR: (
        LocalTuyaEntity(
            id=(DPCode.PIR, DPCode.PIR_STATE),
            device_class=BinarySensorDeviceClass.MOTION,
            custom_configs={CONF_STATE_ON: "pir"},
        ),
        LocalTuyaEntity(
            id=DPCode.STA,
            device_class=BinarySensorDeviceClass.MOTION,
            custom_configs={CONF_STATE_ON: "true"},
        ),
        TAMPER_BINARY_SENSOR,
    ),
    # PM2.5 Sensor
    # https://developer.tuya.com/en/docs/iot/categorypm25?id=Kaiuz3qof3yfu
    "pm2.5": (
        LocalTuyaEntity(
            id=DPCode.PM25_STATE,
            device_class=BinarySensorDeviceClass.SAFETY,
            custom_configs=ALARM_ON,
        ),
        TAMPER_BINARY_SENSOR,
    ),
    # Gas Detector
    # https://developer.tuya.com/en/docs/iot/categoryrqbj?id=Kaiuz3d162ubw
    DeviceCategory.RQBJ: (
        LocalTuyaEntity(
            id=DPCode.GAS_SENSOR_STATUS,
            device_class=BinarySensorDeviceClass.GAS,
            custom_configs=ALARM_ON,
        ),
        LocalTuyaEntity(
            id=DPCode.GAS_SENSOR_STATE,
            device_class=BinarySensorDeviceClass.GAS,
            custom_configs=ON_1,
        ),
        TAMPER_BINARY_SENSOR,
    ),
    # Water Detector
    # https://developer.tuya.com/en/docs/iot/categorysj?id=Kaiuz3iub2sli
    DeviceCategory.SJ: (
        LocalTuyaEntity(
            id=DPCode.WATERSENSOR_STATE,
            device_class=BinarySensorDeviceClass.MOISTURE,
            custom_configs=ALARM_ON,
        ),
        TAMPER_BINARY_SENSOR,
    ),
    # Emergency Button
    # https://developer.tuya.com/en/docs/iot/categorysos?id=Kaiuz3oi6agjy
    DeviceCategory.SOS: (
        LocalTuyaEntity(
            id=DPCode.SOS_STATE,
            device_class=BinarySensorDeviceClass.SAFETY,
            custom_configs=STATE_TRUE,
        ),
        TAMPER_BINARY_SENSOR,
    ),
    # Volatile Organic Compound Sensor
    # Note: Undocumented in cloud API docs, based on test device
    DeviceCategory.VOC: (
        LocalTuyaEntity(
            id=DPCode.VOC_STATE,
            device_class=BinarySensorDeviceClass.SAFETY,
            custom_configs=ALARM_ON,
        ),
        TAMPER_BINARY_SENSOR,
    ),
    # Thermostatic Radiator Valve
    # Not documented
    DeviceCategory.WKF: (
        LocalTuyaEntity(
            id=DPCode.WINDOW_STATE,
            device_class=BinarySensorDeviceClass.WINDOW,
            custom_configs=ON_OPENED,
        ),
    ),
    # Temperature and Humidity Sensor
    # https://developer.tuya.com/en/docs/iot/categorywsdcg?id=Kaiuz3hinij34
    DeviceCategory.WSDCG: (TAMPER_BINARY_SENSOR,),
    # Pressure Sensor
    # https://developer.tuya.com/en/docs/iot/categoryylcg?id=Kaiuz3kc2e4gm
    DeviceCategory.YLCG: (
        LocalTuyaEntity(
            id=DPCode.PRESSURE_STATE,
            custom_configs=ALARM_ON,
        ),
        TAMPER_BINARY_SENSOR,
    ),
    # Smoke Detector
    # https://developer.tuya.com/en/docs/iot/categoryywbj?id=Kaiuz3f6sf952
    DeviceCategory.YWBJ: (
        LocalTuyaEntity(
            id=DPCode.SMOKE_SENSOR_STATUS,
            device_class=BinarySensorDeviceClass.SMOKE,
            custom_configs=ALARM_ON,
        ),
        LocalTuyaEntity(
            id=DPCode.SMOKE_SENSOR_STATE,
            device_class=BinarySensorDeviceClass.SMOKE,
            custom_configs=ALARM_ON,
            condition_contains_any=["alarm"],
        ),
        LocalTuyaEntity(
            id=DPCode.SMOKE_SENSOR_STATE,
            device_class=BinarySensorDeviceClass.SMOKE,
            custom_configs=ON_1,
        ),
        TAMPER_BINARY_SENSOR,
    ),
    # Vibration Sensor
    # https://developer.tuya.com/en/docs/iot/categoryzd?id=Kaiuz3a5vrzno
    DeviceCategory.ZD: (
        LocalTuyaEntity(
            id=(DPCode.SHOCK_STATE, f"{DPCode.SHOCK_STATE}_vibration"),
            device_class=BinarySensorDeviceClass.VIBRATION,
            custom_configs={CONF_STATE_ON: "vibration"},
            condition_contains_any=["tilt", "true"],
        ),
        LocalTuyaEntity(
            id=(DPCode.SHOCK_STATE, f"{DPCode.SHOCK_STATE}_drop"),
            icon="mdi:icon=package-down",
            custom_configs={CONF_STATE_ON: "drop"},
            condition_contains_any=["tilt", "true"],
        ),
        LocalTuyaEntity(
            id=(DPCode.SHOCK_STATE, f"{DPCode.SHOCK_STATE}_tilt"),
            name="Tilt",
            icon="mdi:spirit-level",
            custom_configs={CONF_STATE_ON: "tilt"},
            condition_contains_any=["tilt", "true"],
        ),
    ),
    # EV Charcher
    # https://developer.tuya.com/en/docs/iot/categoryqn?id=Kaiuz18kih0sm
    DeviceCategory.QCCDZ: (*FAULT_SENSOR,),
    # Weather Station
    DeviceCategory.QXJ: (TAMPER_BINARY_SENSOR,),
    # Siren Alarm
    # https://developer.tuya.com/en/docs/iot/categorysgbj?id=Kaiuz37tlpbnu
    DeviceCategory.SGBJ: (
        LocalTuyaEntity(
            id=DPCode.CHARGE_STATE,
            device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
            custom_configs=STATE_TRUE,
        ),
        TAMPER_BINARY_SENSOR,
    ),
    # Gateway control
    # https://developer.tuya.com/en/docs/iot/wg?id=Kbcdadk79ejok
    DeviceCategory.WG2: (
        LocalTuyaEntity(
            id=DPCode.MASTER_STATE,
            device_class=BinarySensorDeviceClass.PROBLEM,
            entity_category=EntityCategory.DIAGNOSTIC,
            custom_configs=ALARM_ON,
        ),
        LocalTuyaEntity(
            id=DPCode.CHARGE_STATE,
            device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
            entity_category=EntityCategory.DIAGNOSTIC,
            custom_configs=STATE_TRUE,
        ),
    ),
}

BINARY_SENSORS[DeviceCategory.GCJ] = FAULT_SENSOR
BINARY_SENSORS[DeviceCategory.CL] = FAULT_SENSOR
BINARY_SENSORS[DeviceCategory.WK] = (
    LocalTuyaEntity(
        id=DPCode.VALVE_STATE,
        name="Valve",
        custom_configs=ON_OPEN,
    ),
    *FAULT_SENSOR,
)
BINARY_SENSORS[DeviceCategory.KG] = FAULT_SENSOR
BINARY_SENSORS[DeviceCategory.PC] = FAULT_SENSOR
BINARY_SENSORS[DeviceCategory.CZ] = FAULT_SENSOR
BINARY_SENSORS[DeviceCategory.CS] = FAULT_SENSOR
BINARY_SENSORS[DeviceCategory.JSQ] = FAULT_SENSOR
BINARY_SENSORS[DeviceCategory.KT] = FAULT_SENSOR
BINARY_SENSORS[DeviceCategory.SD] = FAULT_SENSOR
BINARY_SENSORS[DeviceCategory.SFKZQ] = FAULT_SENSOR
