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

# All descriptions can be found here:
# https://developer.tuya.com/en/docs/iot/standarddescription?id=K9i5ql6waswzq
SIRENS: dict[DeviceCategory, tuple[LocalTuyaEntity, ...]] = {
    # CO2 Detector
    # https://developer.tuya.com/en/docs/iot/categoryco2bj?id=Kaiuz3wes7yuy
    DeviceCategory.CO2BJ: (
        LocalTuyaEntity(
            translation_key="siren",
            id=DPCode.ALARM_SWITCH,
            entity_category=EntityCategory.CONFIG,
            name="Siren",
        ),
    ),
    # Multi-functional Sensor
    # https://developer.tuya.com/en/docs/iot/categorydgnbj?id=Kaiuz3yorvzg3
    DeviceCategory.DGNBJ: (
        LocalTuyaEntity(
            id=(DPCode.ALARM_SWITCH, DPCode.ALARMSWITCH),
        ),
    ),
    # Siren Alarm
    # https://developer.tuya.com/en/docs/iot/categorysgbj?id=Kaiuz37tlpbnu
    DeviceCategory.SGBJ: (
        LocalTuyaEntity(
            id=(DPCode.ALARM_SWITCH, DPCode.ALARMSWITCH),
        ),
    ),
    # Smart Camera
    # https://developer.tuya.com/en/docs/iot/categorysp?id=Kaiuz35leyo12
    DeviceCategory.SP: (
        LocalTuyaEntity(
            translation_key="siren_switch",
            id=DPCode.SIREN_SWITCH,
        ),
    ),
}

# Smart Camera - Low power consumption camera (duplicate of `sp`)
# https://github.com/home-assistant/core/issues/132844
SIRENS[DeviceCategory.DGHSXJ] = SIRENS[DeviceCategory.SP]
