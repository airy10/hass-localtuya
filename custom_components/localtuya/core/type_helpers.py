"""Type helpers for Tuya datapoints (ported from ha_tuya_ble, pass 2).

Provides IntegerTypeData/EnumTypeData (cloud-spec type parsing) and
find_dpcode/find_dpid/get_dptype (code<->dp_id resolution) shared by both
transports. Ported from ha_tuya_ble base.py/devices.py/util.py (2026.5.14).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from ..const import DPType
from .ha_entities.base import DPCode


def remap_value(
    value: float | int,
    from_min: float | int = 0,
    from_max: float | int = 255,
    to_min: float | int = 0,
    to_max: float | int = 255,
    reverse: bool = False,
) -> float:
    """Remap a value from its current range, to a new range."""
    if reverse:
        value = from_max - value + from_min
    return ((value - from_min) / (from_max - from_min)) * (to_max - to_min) + to_min


@dataclass
class IntegerTypeData:
    """Integer Type Data."""

    dpcode: DPCode
    min: int
    max: int
    scale: float
    step: float
    unit: str | None = None
    type: str | None = None

    @property
    def max_scaled(self) -> float:
        """Return the max scaled."""
        return self.scale_value(self.max)

    @property
    def min_scaled(self) -> float:
        """Return the min scaled."""
        return self.scale_value(self.min)

    @property
    def step_scaled(self) -> float:
        """Return the step scaled."""
        return self.step / (10**self.scale)

    def scale_value(self, value: float | int) -> float:
        """Scale a value."""
        return value / (10**self.scale)

    def scale_value_back(self, value: float | int) -> int:
        """Return raw value for scaled."""
        return int(value * (10**self.scale))

    def remap_value_to(
        self,
        value: float,
        to_min: float | int = 0,
        to_max: float | int = 255,
        reverse: bool = False,
    ) -> float:
        """Remap a value from this range to a new range."""
        return remap_value(value, self.min, self.max, to_min, to_max, reverse)

    def remap_value_from(
        self,
        value: float,
        from_min: float | int = 0,
        from_max: float | int = 255,
        reverse: bool = False,
    ) -> float:
        """Remap a value from its current range to this range."""
        return remap_value(value, from_min, from_max, self.min, self.max, reverse)

    @classmethod
    def from_json(cls, dpcode: DPCode, data: str | dict) -> IntegerTypeData | None:
        """Load JSON string and return a IntegerTypeData object."""

        if isinstance(data, str):
            parsed = json.loads(data)
        else:
            parsed = data

        if parsed is None:
            return

        return cls(
            dpcode,
            min=int(parsed["min"]),
            max=int(parsed["max"]),
            scale=float(parsed["scale"]),
            step=max(float(parsed["step"]), 1),
            unit=parsed.get("unit"),
            type=parsed.get("type"),
        )

    @classmethod
    def from_dict(cls, dpcode: DPCode, data: dict | None) -> IntegerTypeData | None:
        """Load Dict and return a IntegerTypeData object."""

        if not data:
            return None

        return cls(
            dpcode,
            min=int(data.get("min", 0)),
            max=int(data.get("max", 0)),
            scale=float(data.get("scale", 0)),
            step=max(float(data.get("step", 0)), 1),
            unit=data.get("unit"),
            type=data.get("type"),
        )


@dataclass
class EnumTypeData:
    """Enum Type Data."""

    dpcode: DPCode
    range: list[str]

    @classmethod
    def from_json(cls, dpcode: DPCode, data: str) -> EnumTypeData | None:
        """Load JSON string and return a EnumTypeData object."""
        if not (parsed := json.loads(data)):
            return None
        return cls(dpcode, **parsed)


def find_dpid(
    dpcode: DPCode | None,
    status_range: dict,
    function: dict,
    prefer_function: bool = False,
) -> int | None:
    """Return the dp id for the given code."""
    if dpcode is None:
        return None
    order = ["status_range", "function"]
    if prefer_function:
        order = ["function", "status_range"]
    for key in order:
        d = status_range if key == "status_range" else function
        if dpcode in d:
            return d[dpcode].dp_id
    return None


def find_dpcode(
    dpcodes: str | DPCode | tuple[DPCode, ...] | None,
    status_range: dict,
    function: dict,
    status: dict | None = None,
    *,
    prefer_function: bool = False,
    dptype: DPType | None = None,
) -> DPCode | EnumTypeData | IntegerTypeData | None:
    """Find a matching DP code available for this device."""
    if dpcodes is None:
        return None
    if isinstance(dpcodes, str):
        dpcodes = (DPCode(dpcodes),)
    elif not isinstance(dpcodes, tuple):
        dpcodes = (dpcodes,)
    order = ["status_range", "function"]
    if prefer_function:
        order = ["function", "status_range"]
    if not dptype:
        order.append("status")
    for dpcode in dpcodes:
        for key in order:
            d = {"status_range": status_range, "function": function, "status": status}.get(key)
            if d is None or dpcode not in d:
                continue
            if dptype == DPType.ENUM and d[dpcode].type == DPType.ENUM:
                if not (enum_type := EnumTypeData.from_json(dpcode, d[dpcode].values)):
                    continue
                return enum_type
            if dptype == DPType.INTEGER and d[dpcode].type == DPType.INTEGER:
                if not (integer_type := IntegerTypeData.from_json(dpcode, d[dpcode].values)):
                    continue
                return integer_type
            if dptype not in (DPType.ENUM, DPType.INTEGER):
                return dpcode
    return None


def get_dptype(
    dpcode: DPCode | None,
    status_range: dict,
    function: dict,
    prefer_function: bool = False,
) -> DPType | None:
    """Return the DPType for a code."""
    if dpcode is None:
        return None
    order = ["status_range", "function"]
    if prefer_function:
        order = ["function", "status_range"]
    for key in order:
        d = status_range if key == "status_range" else function
        if dpcode in d:
            return DPType(d[dpcode].type)
    return None