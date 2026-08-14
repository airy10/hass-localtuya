"""Composable DP wrapper decorators for localtuya entities.

These decorators wrap an inner :class:`DPCodeWrapper` (typically a
:class:`RawDPWrapper` for a config-driven DP, or a cloud-spec wrapper
resolved by ``dp_wrapper_by_id``) and own all HA<->device conversion, so
entity methods stay thin one-liner ``_read_wrapper`` /
``_async_send_wrapper_updates`` calls — mirroring HA core's tuya
integration, where conversion lives in wrappers rather than entities.

Composability uses the *public* wrapper interface (``read_device_status`` /
``get_update_commands``): each decorator converts one step and delegates the
rest to its inner wrapper, e.g.
``InversionWrapper(TimedCoverMathWrapper(RawDPWrapper("dp_1")))``.

Each decorator also exposes ``options`` / ``min_value`` / ``max_value`` /
``value_step`` / ``native_unit`` where relevant, so entities can derive their
capabilities directly from the wrapper.
"""

from __future__ import annotations

import base64
import math
import textwrap
from dataclasses import dataclass
from typing import Any

import homeassistant.util.color as color_util
from homeassistant.components.fan import DIRECTION_FORWARD, DIRECTION_REVERSE
from homeassistant.const import PERCENTAGE
from homeassistant.util.percentage import (
    ordered_list_item_to_percentage,
    percentage_to_ordered_list_item,
    percentage_to_ranged_value,
    ranged_value_to_percentage,
)

from ..const import DictSelector
from .dp_wrappers import DPCodeWrapper

__all__ = [
    "DictSelectorWrapper",
    "ScalingIntegerWrapper",
    "PercentageWrapper",
    "InvertedPercentageWrapper",
    "InversionWrapper",
    "TimedCoverMathWrapper",
    "InvertedBooleanWrapper",
    "ClimateTempWrapper",
    "HumidityCoefficientWrapper",
    "FanSpeedPercentageWrapper",
    "FanDirectionWrapper",
    "BrightnessWrapper",
    "ColorTempWrapper",
    "StringColorWrapper",
    "ColorTypeData",
    "map_range",
]


def map_range(
    value: int, from_min: int, from_max: int, to_min=0, to_max=255, reverse=False
):
    """Map a value from one range to another (optionally reversed)."""
    if reverse:
        value = from_max - (value - from_min)

    scale = (to_max - to_min) / (from_max - from_min)
    mapped_value = to_min + (value - from_min) * scale

    return min(max(round(mapped_value), to_min), to_max)


@dataclass
class ColorTypeData:
    """HSV color type data with per-channel min/max (for hue/sat remapping)."""

    h_min: int = 1
    h_max: int = 360
    s_min: int = 1
    s_max: int = 255
    v_min: int = 1
    v_max: int = 255

    @classmethod
    def from_config(cls, config: dict | None) -> "ColorTypeData | None":
        """Build from a config dict (e.g. {"h": {"min":..,"max":..}, ...})."""
        if not config:
            return None
        h = config.get("h", {})
        s = config.get("s", {})
        v = config.get("v", {})
        return cls(
            h_min=int(h.get("min", 1)),
            h_max=int(h.get("max", 360)),
            s_min=int(s.get("min", 1)),
            s_max=int(s.get("max", 255)),
            v_min=int(v.get("min", 1)),
            v_max=int(v.get("max", 255)),
        )

    def remap_h_to(self, value: float) -> float:
        return map_range(value, self.h_min, self.h_max, 0, 360)

    def remap_h_from(self, value: float) -> int:
        return map_range(value, 0, 360, self.h_min, self.h_max)

    def remap_s_to(self, value: float) -> float:
        return map_range(value, self.s_min, self.s_max, 0, 100)

    def remap_s_from(self, value: float) -> int:
        return map_range(value, 0, 100, self.s_min, self.s_max)

    def remap_v_to(self, value: float) -> int:
        return map_range(value, self.v_min, self.v_max, 0, 255)

    def remap_v_from(self, value: float) -> int:
        return map_range(value, 0, 255, self.v_min, self.v_max)


class DecoratorWrapper[T](DPCodeWrapper[T]):
    """Base for a wrapper that decorates an inner wrapper with conversion.

    Subclasses implement :meth:`_to_ha` (inner value -> HA) and
    :meth:`_to_raw` (HA -> inner value); this base delegates the actual
    device read/write to the inner wrapper's public interface so decorators
    compose arbitrarily.
    """

    def __init__(self, inner: DPCodeWrapper[Any]) -> None:
        super().__init__(
            dpcode=getattr(inner, "dpcode", None),
            dp_id=getattr(inner, "dp_id", None),
        )
        self._inner = inner

    def skip_update(
        self,
        device: Any,
        updated_status_properties: list[str],
        dp_timestamps: dict[str, int] | None = None,
    ) -> bool:
        """Delegate skip decisions to the inner wrapper."""
        if (skip := getattr(self._inner, "skip_update", None)) is not None:
            return skip(device, updated_status_properties, dp_timestamps)
        return self.dpcode not in (updated_status_properties or [])

    def _read_inner(self, device: Any) -> Any | None:
        """Read the inner wrapper's value."""
        return self._inner.read_device_status(device)

    def _write_inner(self, device: Any, value: Any) -> list[dict[str, Any]]:
        """Write a converted value through the inner wrapper."""
        return self._inner.get_update_commands(device, value)

    def read_device_status(self, device: Any) -> T | None:
        """Read the inner value and convert to HA."""
        raw = self._read_inner(device)
        return None if raw is None else self._to_ha(raw)

    def get_update_commands(self, device: Any, value: T) -> list[dict[str, Any]]:
        """Convert a HA value and delegate the write to the inner wrapper."""
        return self._write_inner(device, self._to_raw(value))

    def _to_ha(self, raw: Any) -> T:
        """Convert an inner value to a Home Assistant value."""
        raise NotImplementedError

    def _to_raw(self, value: T) -> Any:
        """Convert a Home Assistant value to an inner value."""
        raise NotImplementedError


class DictSelectorWrapper(DecoratorWrapper[str]):
    """Wraps raw DP value through a DictSelector (select/climate/humidifier/etc)."""

    def __init__(
        self, inner: DPCodeWrapper[Any], options: DictSelector, default=None
    ) -> None:
        super().__init__(inner)
        self._selector = options
        self._default = default

    @property
    def options(self) -> list:
        return self._selector.names

    def _to_ha(self, raw: Any) -> str:
        return self._selector.to_ha(raw, self._default)

    def _to_raw(self, value: str) -> Any:
        return self._selector.to_tuya(value)

    def _raw_value(self, device: Any) -> Any | None:
        """Read the raw device value without the inner wrapper's validation.

        The DictSelector is the authoritative value mapping. The cloud enum
        range can be wrong (e.g. ``relay_status`` reports ``on`` while the spec
        declares ``power_on``), so the value must be mapped directly instead of
        being rejected by the inner ``EnumTypeInformation`` first.
        """
        status = getattr(device, "status", {}) or {}
        if self.dpcode is not None and self.dpcode in status:
            return status[self.dpcode]
        if self.dp_id is not None and str(self.dp_id) in status:
            return status[str(self.dp_id)]
        return None

    def read_device_status(self, device: Any) -> str | None:
        """Read the raw value and map it through the DictSelector."""
        raw = self._raw_value(device)
        return None if raw is None else self._to_ha(raw)

    def get_update_commands(self, device: Any, value: str) -> list[dict[str, Any]]:
        """Write the DictSelector-mapped raw value directly.

        Bypasses the inner wrapper's ``prepare_set_value`` validation for the
        same reason as ``read_device_status``: the cloud enum range can be
        wrong, so the mapped value must be sent as-is.
        """
        return [
            {
                "code": self.dpcode,
                "dp_id": self.dp_id,
                "value": self._to_raw(value),
            }
        ]


class ScalingIntegerWrapper(DecoratorWrapper[float]):
    """Wraps raw integer DP with min/max/step/unit and a linear scale.

    ``scale`` is a multiplier applied on read (``value = raw * scale``) and a
    divisor on write (``raw = round(value / scale)``). Leave ``scale=None``
    for a 1:1 pass-through.
    """

    def __init__(
        self,
        inner: DPCodeWrapper[Any],
        min_value: float | None = None,
        max_value: float | None = None,
        step: float | None = None,
        unit: str | None = None,
        scale: float | None = None,
    ) -> None:
        super().__init__(inner)
        self.min_value = min_value
        self.max_value = max_value
        self.value_step = step
        self.native_unit = unit
        self._scale = scale

    def _to_ha(self, raw: Any) -> float:
        return raw * self._scale if self._scale is not None else raw

    def _to_raw(self, value: float) -> Any:
        if self._scale is not None:
            value = value / self._scale
        return round(value)


class PercentageWrapper(DecoratorWrapper[int]):
    """Wraps raw integer DP as a 0..100 percentage (with optional scale)."""

    def __init__(
        self, inner: DPCodeWrapper[Any], scale: float | None = None
    ) -> None:
        super().__init__(inner)
        self.min_value = 0
        self.max_value = 100
        self.value_step = 1
        self.native_unit = PERCENTAGE
        self._scale = scale

    def _to_ha(self, raw: Any) -> int:
        return round(raw * self._scale) if self._scale is not None else raw

    def _to_raw(self, value: int) -> Any:
        if self._scale is not None:
            value = value / self._scale
        return round(value)


class InvertedPercentageWrapper(PercentageWrapper):
    """Wraps a percentage DP with inversion (100 - value)."""

    def _to_ha(self, raw: Any) -> int:
        return 100 - super()._to_ha(raw)

    def _to_raw(self, value: int) -> Any:
        return super()._to_raw(100 - value)


class InversionWrapper(DecoratorWrapper[int]):
    """Inverts a value: value -> max - value (configurable max)."""

    def __init__(self, inner: DPCodeWrapper[Any], max_value: int = 100) -> None:
        super().__init__(inner)
        self._max = max_value

    def _to_ha(self, raw: Any) -> int:
        return self._max - raw

    def _to_raw(self, value: int) -> Any:
        return self._max - value


class TimedCoverMathWrapper(DecoratorWrapper[int]):
    """Wraps timed cover DP: round(raw * 65535 / 100) for position.

    Mirrors core's ``ControlBackModePercentageMappingWrapper``. Not used by
    localtuya covers (whose timed mode is span_time-based), kept for parity.
    """

    def _to_ha(self, raw: Any) -> int:
        return round(raw * 65535 / 100)

    def _to_raw(self, value: int) -> Any:
        return round(value * 100 / 65535)


class InvertedBooleanWrapper(DecoratorWrapper[bool]):
    """Inverts a boolean DP value (True -> False, False -> True)."""

    def _to_ha(self, raw: Any) -> bool:
        return not raw

    def _to_raw(self, value: bool) -> Any:
        return not value


class ClimateTempWrapper(DecoratorWrapper[float]):
    """Wraps a temperature DP with precision scaling and optional unit convert.

    Read: ``value = raw * precision`` (then ``unit_from(value)`` if given).
    Write: ``raw = round(unit_to(value) / precision)`` (``unit_to`` first).
    """

    def __init__(
        self,
        inner: DPCodeWrapper[Any],
        precision: float = 0.1,
        unit_from=None,
        unit_to=None,
    ) -> None:
        super().__init__(inner)
        self._precision = precision
        self._unit_from = unit_from
        self._unit_to = unit_to

    def _to_ha(self, raw: Any) -> float:
        value = raw * self._precision
        if self._unit_from is not None:
            value = self._unit_from(value)
        return value

    def _to_raw(self, value: float) -> Any:
        if self._unit_to is not None:
            value = self._unit_to(value)
        return round(value / self._precision)


class HumidityCoefficientWrapper(DecoratorWrapper[int]):
    """Wraps a humidity DP with a coefficient (raw / coeff on read, *coeff on write)."""

    def __init__(self, inner: DPCodeWrapper[Any], coefficient: float = 1.0) -> None:
        super().__init__(inner)
        self._coefficient = coefficient

    def _to_ha(self, raw: Any) -> float:
        return raw / self._coefficient

    def _to_raw(self, value: int) -> Any:
        return round(value * self._coefficient)


class FanSpeedPercentageWrapper(DecoratorWrapper[int]):
    """Wraps a fan speed DP: raw int <-> percentage (ranged or ordered list)."""

    def __init__(
        self,
        inner: DPCodeWrapper[Any],
        speed_range: tuple[int, int],
        ordered_list: list[str] | None = None,
    ) -> None:
        super().__init__(inner)
        self._speed_range = speed_range
        self._ordered_list = (
            ordered_list if (ordered_list and len(ordered_list) > 1) else None
        )

    def _to_ha(self, raw: Any) -> int | None:
        if self._ordered_list is not None:
            if str(raw) in self._ordered_list:
                return ordered_list_item_to_percentage(
                    self._ordered_list, str(raw)
                )
            return None
        return ranged_value_to_percentage(self._speed_range, int(raw))

    def _to_raw(self, value: int) -> Any:
        if self._ordered_list is not None:
            return str(percentage_to_ordered_list_item(self._ordered_list, value))
        return int(math.ceil(percentage_to_ranged_value(self._speed_range, value)))


class FanDirectionWrapper(DecoratorWrapper[str]):
    """Wraps a fan direction DP: raw config string <-> HA direction constant."""

    def __init__(
        self, inner: DPCodeWrapper[Any], forward_value: str, reverse_value: str
    ) -> None:
        super().__init__(inner)
        self._forward = forward_value
        self._reverse = reverse_value

    def _to_ha(self, raw: Any) -> str | None:
        if raw == self._forward:
            return DIRECTION_FORWARD
        if raw == self._reverse:
            return DIRECTION_REVERSE
        return None

    def _to_raw(self, value: str) -> Any:
        if value == DIRECTION_FORWARD:
            return self._forward
        if value == DIRECTION_REVERSE:
            return self._reverse
        return value


class BrightnessWrapper(DecoratorWrapper[int]):
    """Wraps a light brightness DP: device range (lower..upper) <-> 0..255."""

    def __init__(
        self, inner: DPCodeWrapper[Any], lower: int, upper: int
    ) -> None:
        super().__init__(inner)
        self._lower = lower
        self._upper = upper

    def _to_ha(self, raw: Any) -> int:
        return map_range(raw, self._lower, self._upper)

    def _to_raw(self, value: int) -> Any:
        return map_range(value, 0, 255, self._lower, self._upper)


class ColorTempWrapper(DecoratorWrapper[int]):
    """Wraps a light color-temperature DP: device range <-> Kelvin."""

    def __init__(
        self,
        inner: DPCodeWrapper[Any],
        min_kelvin: int,
        max_kelvin: int,
        lower: int,
        upper: int,
        reverse: bool = False,
    ) -> None:
        super().__init__(inner)
        self._min_kelvin = min_kelvin
        self._max_kelvin = max_kelvin
        self._lower = lower
        self._upper = upper
        self._reverse = reverse

    def _to_ha(self, raw: Any) -> int:
        return map_range(
            raw,
            self._lower,
            self._upper,
            self._min_kelvin,
            self._max_kelvin,
            self._reverse,
        )

    def _to_raw(self, value: int) -> Any:
        return map_range(
            value,
            self._min_kelvin,
            self._max_kelvin,
            self._lower,
            self._upper,
            self._reverse,
        )


class StringColorWrapper(DecoratorWrapper[tuple[float, float, int]]):
    """Wraps a light color DP: string (v1/v2/base64) <-> (hue, sat, brightness).

    Encapsulates the light platform's color encode/decode (``__to_color*`` /
    ``__from_color*``). Brightness is normalized to the Home Assistant 0..255
    scale on read and accepted in 0..255 on write (like core's
    ``ColorDataWrapper``), remapping through the device's lower..upper range
    internally. ``use_raw`` selects the base64 4-byte HHSL format; otherwise
    the v2/hex vs RGB-encoded format is chosen per-value from the current raw
    string length, mirroring the entity's prior behaviour.
    """

    def __init__(
        self,
        inner: DPCodeWrapper[Any],
        color_type_data: ColorTypeData | None,
        upper_brightness: int,
        lower_brightness: int = 0,
        use_raw: bool = False,
    ) -> None:
        super().__init__(inner)
        self._color_type_data = color_type_data
        self._lower_brightness = lower_brightness
        self._upper_brightness = upper_brightness
        self._use_raw = use_raw

    def read_device_status(self, device: Any) -> tuple[float, float, int] | None:
        raw = self._read_inner(device)
        return None if raw is None else self.decode(raw)

    def get_update_commands(
        self, device: Any, value: tuple[float, float, int]
    ) -> list[dict[str, Any]]:
        hue, sat, brightness = value
        current = self._read_inner(device)
        return self._write_inner(device, self.encode(hue, sat, brightness, current))

    def _brightness_to_ha(self, value: int) -> int:
        """Remap a raw device brightness to the Home Assistant 0..255 scale."""
        return map_range(value, self._lower_brightness, self._upper_brightness)

    def _brightness_to_raw(self, value: int) -> int:
        """Remap a Home Assistant 0..255 brightness to the device scale."""
        return map_range(value, 0, 255, self._lower_brightness, self._upper_brightness)

    def decode(self, color: str) -> tuple[float, float, int] | None:
        """Decode a string color to (hue, sat, brightness) in HA units (0..255).

        Brightness is format-specific, mirroring core's per-``v_type`` scaling:
        the v2 and base64 formats store the device-scale value (remapped through
        ``lower..upper``), while the v1/rgb-encoded format stores a 2-hex value
        that is already on the 0..255 scale.
        """
        if self._use_raw:
            hue, sat, value = self._from_color_raw(color)
            value = self._brightness_to_ha(value)
        elif self._is_rgb_encoded(color):
            hue = int(color[6:10], 16)
            sat = int(color[10:12], 16)
            value = int(color[12:14], 16)
            if self._color_type_data:
                hue = self._color_type_data.remap_h_to(hue)
                sat = self._color_type_data.remap_s_to(sat)
            else:
                sat = sat * 100 / 255
        else:
            hue, sat, value = self._from_color_v2(color)
            value = self._brightness_to_ha(value)
        return hue, sat, value

    def encode(
        self,
        hue: float,
        sat: float,
        brightness: int,
        current: str | None = None,
    ) -> str:
        """Encode (hue, sat, brightness 0..255) to a string."""
        if self._use_raw:
            return self._to_color_raw(hue, sat, self._brightness_to_raw(brightness))
        if self._is_rgb_encoded(current):
            # v1/rgb-encoded: the 2-hex value field is already 0..255.
            rgb = color_util.color_hsv_to_RGB(
                hue, sat, int(brightness * 100 / 255)
            )
            if self._color_type_data:
                h = self._color_type_data.remap_h_from(hue)
                s = self._color_type_data.remap_s_from(sat)
            else:
                h = round(hue)
                s = round(sat * 255 / 100)
            return "{:02x}{:02x}{:02x}{:04x}{:02x}{:02x}".format(
                round(rgb[0]), round(rgb[1]), round(rgb[2]), h, s, brightness
            )
        return self._to_color_v2(hue, sat, self._brightness_to_raw(brightness))

    def _to_color_raw(self, hue: float, sat: float, brightness: int) -> str:
        return base64.b64encode(
            bytes(
                [
                    round(hue) // 256,
                    round(hue) % 256,
                    round(sat),
                    round(brightness * 100 / self._upper_brightness),
                ]
            )
        ).decode("ascii")

    def _to_color_v2(self, hue: float, sat: float, brightness: int) -> str:
        if self._color_type_data:
            h = self._color_type_data.remap_h_from(hue)
            s = self._color_type_data.remap_s_from(sat)
        else:
            h = round(hue)
            s = round(sat * 10.0)
        return "{:04x}{:04x}{:04x}".format(h, s, brightness)

    def _from_color_raw(self, color: str) -> tuple[float, float, int]:
        hsl = int.from_bytes(base64.b64decode(color), byteorder="big", signed=False)
        hue = hsl // 65536
        sat = (hsl // 256) % 256
        value = (hsl % 256) * self._upper_brightness / 100
        return hue, sat, value

    def _from_color_v2(self, color: str) -> tuple[float, float, int]:
        hue, sat, value = [int(value, 16) for value in textwrap.wrap(color, 4)]
        if self._color_type_data:
            return (
                self._color_type_data.remap_h_to(hue),
                self._color_type_data.remap_s_to(sat),
                value,
            )
        return hue, sat / 10.0, value

    @staticmethod
    def _is_rgb_encoded(color: str | None) -> bool:
        """Return whether a color string uses the RGB-encoded (7-byte) format."""
        return False if color is None else len(color) > 12
