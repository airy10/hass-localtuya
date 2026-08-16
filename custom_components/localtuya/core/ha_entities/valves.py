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
            id=DPCode.SWITCH,
            name="Valve",
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_1,
            name="Valve 1",
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_2,
            name="Valve 2",
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_3,
            name="Valve 3",
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_4,
            name="Valve 4",
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_5,
            name="Valve 5",
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_6,
            name="Valve 6",
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_7,
            name="Valve 7",
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_8,
            name="Valve 8",
        ),
    ),
}
