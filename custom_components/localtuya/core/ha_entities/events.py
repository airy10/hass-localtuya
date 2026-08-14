"""
    This a file contains available tuya data
    https://developer.tuya.com/en/docs/iot/standarddescription?id=K9i5ql6waswzq

    Credits: official HA Tuya integration.
    Modified by: xZetsubou
"""

from .base import DeviceCategory, LocalTuyaEntity


# Event entities are bus-driven (e.g. the BLE Fingerbot fires
# ``localtuya_fingerbot_button_pressed`` on the HA bus, wrapped by
# ``event.py``), so no DP-table entries are needed here. The table exists to
# keep ``DATA_PLATFORMS`` complete for the auto-config flow.
EVENTS: dict[DeviceCategory, tuple[LocalTuyaEntity, ...]] = {}