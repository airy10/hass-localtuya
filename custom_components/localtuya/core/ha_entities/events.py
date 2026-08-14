"""
    This a file contains available tuya data
    https://developer.tuya.com/en/docs/iot/standarddescription?id=K9i5ql6waswzq

    Credits: official HA Tuya integration.
    Modified by: xZetsubou
"""

from homeassistant.components.event import EventDeviceClass

from .base import DeviceCategory, DPCode, LocalTuyaEntity
from ..dp_wrapper_decorators import (
    Base64Utf8RawEventWrapper,
    Base64Utf8StringEventWrapper,
    SimpleEventEnumWrapper,
)


def _numbered_buttons() -> tuple[LocalTuyaEntity, ...]:
    """Build the nine numbered-button event entities (core's WXKG table)."""
    return tuple(
        LocalTuyaEntity(
            id=getattr(DPCode, f"SWITCH_MODE{i}"),
            name=f"Button {i}",
            device_class=EventDeviceClass.BUTTON,
            wrapper_class=SimpleEventEnumWrapper,
        )
        for i in range(1, 10)
    )


EVENTS: dict[DeviceCategory, tuple[LocalTuyaEntity, ...]] = {
    # Doorbell
    DeviceCategory.SP: (
        LocalTuyaEntity(
            id=DPCode.ALARM_MESSAGE,
            name="Doorbell message",
            device_class=EventDeviceClass.DOORBELL,
            wrapper_class=Base64Utf8StringEventWrapper,
        ),
        LocalTuyaEntity(
            id=DPCode.DOORBELL_PIC,
            name="Doorbell picture",
            device_class=EventDeviceClass.DOORBELL,
            wrapper_class=Base64Utf8RawEventWrapper,
        ),
    ),
    # Remote controller / scene switch
    DeviceCategory.WXKG: _numbered_buttons(),
}
