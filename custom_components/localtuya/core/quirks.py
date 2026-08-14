"""Product-id keyed quirks registry.

Mirrors core tuya's ``QuirksRegistry`` (tuya_device_handlers/registry.py):
a registry keyed by ``product_id`` that lets a specific device model
override generic behavior without touching the category tables.

Our per-product entity mappings already live in ``core/mappings.py``
(``MAPPINGS``). This registry covers the remaining hardcoded per-product
tables that are not entity mappings — e.g. which datapoint a Fingerbot
reports its physical button press on.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DeviceQuirk:
    """Behavior overrides for a specific product_id."""

    # Datapoint id the physical button press is reported on (Fingerbot).
    button_switch_dp: int | None = None


class QuirksRegistry:
    """Registry for LocalTuya quirks."""

    _quirks: dict[str, DeviceQuirk]

    def __init__(self) -> None:
        """Initialize the registry."""
        self._quirks = {}

    def register(self, product_id: str, quirk: DeviceQuirk) -> None:
        """Register a quirk for a specific device type."""
        self._quirks[product_id] = quirk

    def get_quirk_for_device(self, device: Any) -> DeviceQuirk | None:
        """Get the quirk for a specific device."""
        product_id = getattr(device, "product_id", None)
        if product_id is None:
            return None
        return self._quirks.get(product_id)


# Fingerbot product IDs and the datapoint their physical button press is
# reported on (mirrors the previous hardcoded ``FINGERBOT_SWITCH_DP`` table).
FINGERBOT_SWITCH_DP: dict[str, int] = {
    "3yqdo5yt": 1,  # CUBETOUCH 1s
    "xhf790if": 1,  # CUBETOUCH II
    "blliqpsj": 2,  # Fingerbot Plus
    "ndvkgsrm": 2,
    "yiihr7zh": 2,
    "neq16kgd": 2,
    "ltak7e1p": 2,  # Fingerbot
    "y6kttvd6": 2,
    "yrnk7mnn": 2,
    "nvr2rocq": 2,
    "bnt7wajf": 2,
    "rvdceqjh": 2,
    "5xhbk964": 2,
}


def _build_fingerbot_quirks() -> dict[str, DeviceQuirk]:
    """Build quirks from the fingerbot product table."""
    return {
        product_id: DeviceQuirk(button_switch_dp=dp_id)
        for product_id, dp_id in FINGERBOT_SWITCH_DP.items()
    }


QUIRKS_REGISTRY = QuirksRegistry()
for _product_id, _quirk in _build_fingerbot_quirks().items():
    QUIRKS_REGISTRY.register(_product_id, _quirk)
