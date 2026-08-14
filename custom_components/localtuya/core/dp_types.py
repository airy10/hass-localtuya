"""DP type information (capability specs) for Tuya datapoints.

VENDORED from the HA core ``tuya`` integration (libs ``tuya_device_handlers``
package, ``type_information.py``; pinned in core manifest as
``tuya-device-handlers==0.0.26``).  We intentionally do NOT import that
package at runtime: the core component pins its own release and its internals
may change without notice.  This module is a transport-agnostic copy so our
entity logic can mirror the core integration without breaking when the core
component is updated.

SYNC CHECKLIST (when the core component is updated):
  1. Diff ``homeassistant/components/tuya/tuya_device_handlers/type_information.py``
     against this file.
  2. Port: new TypeInformation subclasses, changes to ``find_dpcode``,
     ``prepare_set_value``/``read_device_value`` conversion rules, the
     ``_DPTYPE_MAPPING`` ill-formed-type fixups (see ``const.DPType.try_parse``).
  3. Our deliberate deltas (keep, they are intentional):
     - no ``CustomerDevice`` dependency: the device argument is a duck-typed
       object exposing ``function``/``status_range``/``status`` dicts keyed by
       dpcode plus ``id``/``product_id`` (our ``TuyaDevice`` provides them).
     - ``_from_json`` accepts BOTH JSON strings (Ethernet cloud dps_data) and
       pre-parsed dicts (BLE ``TuyaBLEDeviceFunction.values``).
     - no ``type_information_cls`` quirk overrides: spec-patching quirks are
       applied to ``TuyaDevice.function``/``status_range`` *before* this layer
       reads them (``core/quirks.py``), so the ``TypeInformation`` built here
       already reflects any per-product fixes.
"""

from __future__ import annotations

import abc
import base64
import binascii
import json
import logging
from dataclasses import dataclass
from typing import Any, ClassVar, Self

from ..const import DPType

_LOGGER = logging.getLogger(__name__)

_LOG_OR_QUIRK = (
    "please report this defect to Tuya support, or create a quirk "
    "at https://github.com/home-assistant-libs/tuya-device-handlers"
)

_DEVICE_WARNINGS: dict[str, set[str]] = {}


class PrepareSetValueError(ValueError):
    """A value could not be prepared to be sent to a Tuya data point."""


def _should_log_warning(device_id: str, warning_key: str) -> bool:
    """Check if a warning was already logged for a device."""
    if (device_warnings := _DEVICE_WARNINGS.get(device_id)) is None:
        device_warnings = set()
        _DEVICE_WARNINGS[device_id] = device_warnings
    if warning_key in device_warnings:
        return False
    _DEVICE_WARNINGS[device_id].add(warning_key)
    return True


def _get_spec_attr(spec: Any, name: str) -> Any:
    """Return an attribute from a spec entry that is an object or a dict."""
    if isinstance(spec, dict):
        return spec.get(name)
    return getattr(spec, name, None)


@dataclass(kw_only=True)
class TypeInformation[T](abc.ABC):
    """Type information.

    As provided by the cloud, from ``device.function`` / ``device.status_range``.
    """

    _DPTYPE: ClassVar[DPType]
    dpcode: str
    type_data: str
    report_type: str | None

    @classmethod
    def _from_json(
        cls,
        dpcode: str,
        type_data: str | dict | list,
        *,
        report_type: str | None,
    ) -> Self | None:
        """Load a JSON string (or pre-parsed values) and return a TypeInformation object."""
        return cls(dpcode=dpcode, type_data=type_data, report_type=report_type)

    @classmethod
    def find_dpcode(
        cls,
        device: Any,
        dpcodes: str | tuple[str, ...] | None,
        *,
        prefer_function: bool = False,
    ) -> Self | None:
        """Find type information for a matching DP code."""
        if dpcodes is None:
            return None

        if not isinstance(dpcodes, tuple):
            dpcodes = (dpcodes,)

        lookup_tuple = (
            (device.function, device.status_range)
            if prefer_function
            else (device.status_range, device.function)
        )

        for dpcode in dpcodes:
            for device_specs in lookup_tuple:
                if (current_definition := device_specs.get(dpcode)) is None:
                    continue
                type_str = _get_spec_attr(current_definition, "type")
                if (
                    type_str is not None
                    and DPType.try_parse(type_str) is cls._DPTYPE
                    and (
                        type_information := cls._from_json(
                            dpcode=dpcode,
                            type_data=_get_spec_attr(
                                current_definition, "values"
                            ),
                            report_type=_get_spec_attr(
                                current_definition, "report_type"
                            ),
                        )
                    )
                ):
                    return type_information

        return None

    @abc.abstractmethod
    def read_device_value(self, device: Any) -> T | None:
        """Read (and validate + convert) device value."""

    def prepare_set_value(self, device: Any, value: Any) -> Any:
        """Prepare a Home Assistant value to be sent as a device command."""
        raise NotImplementedError


@dataclass(kw_only=True)
class BitmapTypeInformation(TypeInformation[int]):
    """Bitmap type information."""

    _DPTYPE = DPType.BITMAP

    label: list[str]

    @classmethod
    def _from_json(
        cls,
        dpcode: str,
        type_data: str | dict | list,
        *,
        report_type: str | None,
    ) -> Self | None:
        """Load a JSON string (or pre-parsed values) and return a BitmapTypeInformation object."""
        parsed = type_data if isinstance(type_data, dict) else None
        if parsed is None and isinstance(type_data, str):
            try:
                parsed = json.loads(type_data)
            except (TypeError, ValueError):
                parsed = None
        if not parsed:
            return None
        return cls(
            dpcode=dpcode,
            type_data=type_data,
            report_type=report_type,
            label=parsed["label"],
        )

    def read_device_value(self, device: Any) -> int | None:
        """Read the device value for this datapoint."""
        if (raw_value := device.status.get(self.dpcode)) is None:
            return None
        if isinstance(raw_value, int):
            return raw_value
        if _should_log_warning(
            device.id, f"invalid_bitmap|{self.dpcode}|{raw_value}"
        ):
            _LOGGER.warning(
                "Found invalid BITMAP value `%s` (%s) for datapoint `%s` in "
                "product id `%s`; %s",
                raw_value,
                type(raw_value),
                self.dpcode,
                device.product_id,
                _LOG_OR_QUIRK,
            )
        return None


@dataclass(kw_only=True)
class BooleanTypeInformation(TypeInformation[bool]):
    """Boolean type information."""

    _DPTYPE = DPType.BOOLEAN

    def prepare_set_value(self, device: Any, value: Any) -> bool:
        """Prepare a Home Assistant value to be sent as a device command."""
        if not isinstance(value, bool):
            msg = f"Invalid boolean value `{value}` ({type(value).__name__})"
            raise PrepareSetValueError(msg)
        return value

    def read_device_value(self, device: Any) -> bool | None:
        """Read the device value for this datapoint."""
        if (raw_value := device.status.get(self.dpcode)) is None:
            return None
        if raw_value in (True, False):
            return raw_value

        if _should_log_warning(
            device.id, f"boolean_out_range|{self.dpcode}|{raw_value}"
        ):
            _LOGGER.warning(
                "Found invalid BOOLEAN value `%s` (%s) for datapoint `%s` in "
                "product id `%s`; %s",
                raw_value,
                type(raw_value),
                self.dpcode,
                device.product_id,
                _LOG_OR_QUIRK,
            )
        return None


@dataclass(kw_only=True)
class EnumTypeInformation(TypeInformation[str]):
    """Enum type information."""

    _DPTYPE = DPType.ENUM

    range: list[str]

    @classmethod
    def _from_json(
        cls,
        dpcode: str,
        type_data: str | dict | list,
        *,
        report_type: str | None,
    ) -> Self | None:
        """Load a JSON string (or pre-parsed values) and return an EnumTypeInformation object."""
        parsed = type_data if isinstance(type_data, dict) else None
        if parsed is None and isinstance(type_data, str):
            try:
                parsed = json.loads(type_data)
            except (TypeError, ValueError):
                parsed = None
        if not parsed:
            return None
        return cls(
            dpcode=dpcode,
            type_data=type_data,
            report_type=report_type,
            range=parsed["range"]
            if "range" in parsed
            else [v for _, v in sorted(parsed.items(), key=lambda kv: int(kv[0]))],
        )

    def prepare_set_value(self, device: Any, value: Any) -> str:
        """Prepare a Home Assistant value to be sent as a device command."""
        if not isinstance(value, str):
            msg = f"Invalid string value `{value}` ({type(value).__name__})"
            raise PrepareSetValueError(msg)
        if value not in self.range:
            msg = f"Enum value `{value}` out of range: {self.range}"
            raise PrepareSetValueError(msg)
        return value

    def read_device_value(self, device: Any) -> str | None:
        """Read the device value for this datapoint."""
        if (raw_value := device.status.get(self.dpcode)) is None:
            return None
        if raw_value in self.range:
            return raw_value

        if _should_log_warning(
            device.id, f"enum_out_range|{self.dpcode}|{raw_value}"
        ):
            _LOGGER.warning(
                "Found invalid ENUM value `%s` (%s) for datapoint `%s` in "
                "product id `%s`, expected one of `%s`; %s",
                raw_value,
                type(raw_value),
                self.dpcode,
                device.product_id,
                self.range,
                _LOG_OR_QUIRK,
            )
        return None


@dataclass(kw_only=True)
class IntegerTypeInformation(TypeInformation[float]):
    """Integer type information."""

    _DPTYPE = DPType.INTEGER

    min: int
    max: int
    scale: int
    step: int
    unit: str | None = None

    def scale_value(self, value: int) -> float:
        """Scale a value."""
        return value / (10**self.scale)

    def scale_value_back(self, value: float) -> int:
        """Return raw value for scaled."""
        return round(value * (10**self.scale))

    @classmethod
    def _from_json(
        cls,
        dpcode: str,
        type_data: str | dict | list,
        *,
        report_type: str | None,
    ) -> Self | None:
        """Load a JSON string (or pre-parsed values) and return an IntegerTypeInformation object."""
        parsed = type_data if isinstance(type_data, dict) else None
        if parsed is None and isinstance(type_data, str):
            try:
                parsed = json.loads(type_data)
            except (TypeError, ValueError):
                parsed = None
        if not parsed:
            return None

        return cls(
            dpcode=dpcode,
            type_data=type_data,
            min=int(parsed["min"]),
            max=int(parsed["max"]),
            scale=int(parsed["scale"]),
            step=int(parsed["step"]),
            unit=parsed.get("unit"),
            report_type=report_type,
        )

    def prepare_set_value(self, device: Any, value: Any) -> int:
        """Prepare a Home Assistant value to be sent as a device command."""
        if not isinstance(value, (int, float)):
            msg = f"Invalid numeric value `{value}` ({type(value).__name__})"
            raise PrepareSetValueError(msg)
        new_value = self.scale_value_back(value)
        if not (self.min <= new_value <= self.max):
            msg = (
                f"Value `{new_value}` (converted from {type(value).__name__}"
                f" `{value}`) out of range: ({self.min}-{self.max})"
            )
            raise PrepareSetValueError(msg)
        return new_value

    def read_device_value(self, device: Any) -> float | None:
        """Read the device value for this datapoint."""
        if (raw_value := device.status.get(self.dpcode)) is None:
            return None
        if isinstance(raw_value, int) and (self.min <= raw_value <= self.max):
            return self.scale_value(raw_value)
        if _should_log_warning(
            device.id, f"integer_out_range|{self.dpcode}|{raw_value}"
        ):
            _LOGGER.warning(
                "Found invalid INTEGER value `%s` (%s) for datapoint `%s` in "
                "product id `%s`, expected value between %s and %s; %s",
                raw_value,
                type(raw_value),
                self.dpcode,
                device.product_id,
                self.min,
                self.max,
                _LOG_OR_QUIRK,
            )

        return None


@dataclass(kw_only=True)
class JsonTypeInformation(TypeInformation[dict[str, Any]]):
    """Json type information."""

    _DPTYPE = DPType.JSON

    def read_device_value(self, device: Any) -> dict[str, Any] | None:
        """Read the device value for this datapoint."""
        if (raw_value := device.status.get(self.dpcode)) is None:
            return None
        try:
            return json.loads(raw_value)
        except (TypeError, ValueError):
            if _should_log_warning(device.id, f"invalid_json|{self.dpcode}"):
                _LOGGER.warning(
                    "Found invalid JSON value `%s` (%s) for datapoint `%s` in "
                    "product id `%s`; %s",
                    raw_value,
                    type(raw_value),
                    self.dpcode,
                    device.product_id,
                    _LOG_OR_QUIRK,
                )
            return None


@dataclass(kw_only=True)
class RawTypeInformation(TypeInformation[bytes]):
    """Raw type information."""

    _DPTYPE = DPType.RAW

    def read_device_value(self, device: Any) -> bytes | None:
        """Read the device value for this datapoint."""
        if (raw_value := device.status.get(self.dpcode)) is None:
            return None
        try:
            return base64.b64decode(raw_value)
        except (binascii.Error, TypeError):
            if _should_log_warning(device.id, f"invalid_raw|{self.dpcode}"):
                _LOGGER.warning(
                    "Found invalid RAW value `%s` (%s) for datapoint `%s` in "
                    "product id `%s`; %s",
                    raw_value,
                    type(raw_value),
                    self.dpcode,
                    device.product_id,
                    _LOG_OR_QUIRK,
                )
        return None


@dataclass(kw_only=True)
class StringTypeInformation(TypeInformation[str]):
    """String type information."""

    _DPTYPE = DPType.STRING

    def read_device_value(self, device: Any) -> str | None:
        """Read the device value for this datapoint."""
        return device.status.get(self.dpcode)