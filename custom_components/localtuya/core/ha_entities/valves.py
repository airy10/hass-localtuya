"""
    This a file contains available tuya data
    https://developer.tuya.com/en/docs/iot/standarddescription?id=K9i5ql6waswzq

    Credits: official HA Tuya integration.
    Modified by: xZetsubou
"""

from .base import DPCode, DeviceCategory, LocalTuyaEntity


VALVES: dict[DeviceCategory, tuple[LocalTuyaEntity, ...]] = {
    # Water Valve
    # https://developer.tuya.com/en/docs/iot/s?id=K9i5ql6waswzq
    DeviceCategory.SFKZQ: (
        LocalTuyaEntity(
            translation_key="valve",
            id=DPCode.SWITCH,
            name="Valve",
        ),
        LocalTuyaEntity(
            translation_key="valve_1",
            id=DPCode.SWITCH_1,
            name="Valve 1",
        ),
        LocalTuyaEntity(
            translation_key="valve_2",
            id=DPCode.SWITCH_2,
            name="Valve 2",
        ),
        LocalTuyaEntity(
            translation_key="valve_3",
            id=DPCode.SWITCH_3,
            name="Valve 3",
        ),
        LocalTuyaEntity(
            translation_key="valve_4",
            id=DPCode.SWITCH_4,
            name="Valve 4",
        ),
        LocalTuyaEntity(
            translation_key="valve_5",
            id=DPCode.SWITCH_5,
            name="Valve 5",
        ),
        LocalTuyaEntity(
            translation_key="valve_6",
            id=DPCode.SWITCH_6,
            name="Valve 6",
        ),
        LocalTuyaEntity(
            translation_key="valve_7",
            id=DPCode.SWITCH_7,
            name="Valve 7",
        ),
        LocalTuyaEntity(
            translation_key="valve_8",
            id=DPCode.SWITCH_8,
            name="Valve 8",
        ),
    ),
}
