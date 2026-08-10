"""
    This a file contains available tuya data
    https://developer.tuya.com/en/docs/iot/standarddescription?id=K9i5ql6waswzq

    Credits: official HA Tuya integration.
    Modified by: xZetsubou
"""

from .base import LocalTuyaEntity

TEXTS: dict[str, tuple[LocalTuyaEntity, ...]] = {}