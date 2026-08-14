"""Tuya DP wrappers (vendored from HA core tuya ``device_wrapper`` package).

VENDORED from ``tuya_device_handlers/device_wrapper/`` (``base.py`` +
``common.py``; pinned in core manifest as ``tuya-device-handlers==0.0.26``).
We intentionally do NOT import that package at runtime: the core component
pins its own release and its internals may change without notice.  This
module is a transport-agnostic copy so our entity logic can mirror the core
integration without breaking when the core component is updated.

SYNC CHECKLIST (when the core component is updated):
  1. Diff ``homeassistant/components/tuya/tuya_device_handlers/device_wrapper/``
     (``base.py`` + ``common.py``) against this file.
  2. Port: new wrapper classes, changes to ``skip_update``/``find_dpcode``/
     ``get_update_commands``/``read_device_status``.
3. Our deliberate deltas (keep, they are intentional):
      - wrappers additionally carry ``dp_id``: our entities are config-driven
        by DP id, so ``dp_wrapper_by_id()`` resolves a wrapper from the
        numeric DP id instead of only the dpcode.
      - ``get_update_commands`` returns ``{"code", "dp_id", "value"}`` so both
        the core-style dpcode commands and our DP-id transport writes work.
      - ``RawDPWrapper`` and ``BitmapMaskWrapper`` are localtuya-only (no
        core equivalent): config-driven entities can point at DPs with no
        cloud spec, so we fall back to a raw wrapper, and ``bitmap_mask``
        entities wrap any wrapper with a bitmask.
"""

from __future__ import annotations

from typing import Any, Self

from ..const import DPType
from .dp_types import (
    BitmapTypeInformation,
    BooleanTypeInformation,
    EnumTypeInformation,
    IntegerTypeInformation,
    JsonTypeInformation,
    PrepareSetValueError,
    RawTypeInformation,
    StringTypeInformation,
    TypeInformation,
)

__all__ = [
    "DeviceWrapper",
    "DPCodeWrapper",
    "DPCodeTypeInformationWrapper",
    "DPCodeBitmapWrapper",
    "DPCodeBooleanWrapper",
    "DPCodeEnumWrapper",
    "DPCodeIntegerWrapper",
    "DPCodeJsonWrapper",
    "DPCodeRawWrapper",
    "DPCodeStringWrapper",
    "RawDPWrapper",
    "BitmapMaskWrapper",
    "SetValueOutOfRangeError",
    "dp_wrapper_by_id",
    "dp_wrapper_by_code",
]


class SetValueOutOfRangeError(ValueError):
    """Attempted to send an invalid value to Tuya data point."""


class DeviceWrapper[T]:
    """Base device wrapper."""

    native_unit: str | None = None
    suggested_unit: str | None = None

    max_value: float
    min_value: float
    value_step: float

    options: list[str]

    def initialize(self, device: Any) -> None:
        """Initialize the wrapper with device data.

        Called when the entity is added to Home Assistant.
        Override in subclasses to perform initialization logic.
        """

    def skip_update(
        self,
        device: Any,
        updated_status_properties: list[str],
        dp_timestamps: dict[str, int] | None = None,
    ) -> bool:
        """Determine if the wrapper should skip an update.

        The default is to always skip, unless overridden in subclasses.
        """
        return True

    def read_device_status(self, device: Any) -> T | None:
        """Read device status and convert to a Home Assistant value."""
        raise NotImplementedError

    def get_update_commands(
        self, device: Any, value: T
    ) -> list[dict[str, Any]]:
        """Generate update commands for a Home Assistant action."""
        raise NotImplementedError


class DPCodeWrapper[T](DeviceWrapper[T]):
    """Base device wrapper for a single DPCode.

    Used as a common interface for referring to a DPCode, and
    access read conversion routines.
    """

    def __init__(self, dpcode: str, dp_id: int | str | None = None) -> None:
        """Init DPCodeWrapper."""
        self.dpcode = dpcode
        self.dp_id = dp_id

    def skip_update(
        self,
        device: Any,
        updated_status_properties: list[str],
        dp_timestamps: dict[str, int] | None = None,
    ) -> bool:
        """Determine if the wrapper should skip an update.

        By default, skip if updated_status_properties is not given or
        does not include this dpcode.
        """
        return self.dpcode not in updated_status_properties

    def read_device_status(self, device: Any) -> T | None:
        """Read device status and convert to a Home Assistant value."""
        return self._read_dpcode_value(device)

    def _read_dpcode_value(self, device: Any) -> Any | None:
        """Read the DPCode value.

        Base implementation returns the raw value, subclasses
        may override to provide specific conversion or
        validation.
        """
        return device.status.get(self.dpcode)

    def _convert_value_to_raw_value(self, device: Any, value: Any) -> Any:
        """Convert display value back to a raw device value.

        Base implementation does no validation, subclasses may
        override to provide specific validation.
        """
        raise NotImplementedError

    def get_update_commands(
        self, device: Any, value: T
    ) -> list[dict[str, Any]]:
        """Get the update commands for the dpcode.

        The Home Assistant value is converted back to a raw device value.
        """
        return [
            {
                "code": self.dpcode,
                "dp_id": self.dp_id,
                "value": self._convert_value_to_raw_value(device, value),
            }
        ]


class DPCodeTypeInformationWrapper[
    TypeInformationT: TypeInformation[Any],
    UnderlyingT,
    T,
](DPCodeWrapper[T]):
    """Base DPCode wrapper with Type Information."""

    _DPTYPE: type[TypeInformationT]
    type_information: TypeInformationT

    def __init__(
        self,
        dpcode: str,
        type_information: TypeInformationT,
        dp_id: int | str | None = None,
    ) -> None:
        """Init DPCodeWrapper."""
        super().__init__(dpcode, dp_id)
        self.type_information = type_information

    @classmethod
    def find_dpcode(
        cls,
        device: Any,
        dpcodes: str | tuple[str, ...] | None,
        *,
        prefer_function: bool = False,
    ) -> Self | None:
        """Find a DPCodeTypeInformationWrapper for the given DP codes."""
        if type_information := cls._DPTYPE.find_dpcode(
            device, dpcodes, prefer_function=prefer_function
        ):
            return cls(
                dpcode=type_information.dpcode,
                type_information=type_information,
            )
        return None

    @classmethod
    def find_dpid(
        cls,
        device: Any,
        dp_id: int | str | None,
        *,
        prefer_function: bool = False,
    ) -> Self | None:
        """Find a DPCodeTypeInformationWrapper matching a numeric DP id.

        Localtuya entities are config-driven by DP id, so this resolves a
        wrapper from the entity's DP id instead of a dpcode.
        """
        if dp_id is None:
            return None
        lookup_tuple = (
            (device.function, device.status_range)
            if prefer_function
            else (device.status_range, device.function)
        )
        for device_specs in lookup_tuple:
            for dpcode, spec in device_specs.items():
                if str(_spec_dp_id(spec)) != str(dp_id):
                    continue
                if wrapper := cls.find_dpcode(
                    device, dpcode, prefer_function=prefer_function
                ):
                    wrapper.dp_id = dp_id
                    return wrapper
        return None

    def _read_dpcode_value(self, device: Any) -> UnderlyingT | None:
        """Read and process raw value against this type information."""
        return self.type_information.read_device_value(device)

    def _convert_value_to_raw_value(self, device: Any, value: Any) -> Any:
        """Convert a Home Assistant value back to a raw device value."""
        try:
            return self.type_information.prepare_set_value(device, value)
        except PrepareSetValueError as err:
            raise SetValueOutOfRangeError(str(err)) from err


def _spec_dp_id(spec: Any) -> int | str | None:
    """Return the DP id from a spec entry that is an object or a dict."""
    if isinstance(spec, dict):
        return spec.get("dp_id")
    return getattr(spec, "dp_id", None)


class DPCodeBitmapWrapper[T = int](
    DPCodeTypeInformationWrapper[BitmapTypeInformation, int, T]
):
    """Simple wrapper for BitmapTypeInformation values."""

    _DPTYPE = BitmapTypeInformation


class DPCodeBooleanWrapper[T = bool](
    DPCodeTypeInformationWrapper[BooleanTypeInformation, bool, T]
):
    """Simple wrapper for BooleanTypeInformation values."""

    _DPTYPE = BooleanTypeInformation


class DPCodeEnumWrapper[T = str](
    DPCodeTypeInformationWrapper[EnumTypeInformation, str, T]
):
    """Simple wrapper for EnumTypeInformation values."""

    _DPTYPE = EnumTypeInformation
    options: list[str]

    def __init__(
        self,
        dpcode: str,
        type_information: EnumTypeInformation,
        dp_id: int | str | None = None,
    ) -> None:
        """Init DPCodeEnumWrapper."""
        super().__init__(dpcode, type_information, dp_id)
        self.options = type_information.range


class DPCodeIntegerWrapper[T = float](
    DPCodeTypeInformationWrapper[IntegerTypeInformation, float, T]
):
    """Simple wrapper for IntegerTypeInformation values."""

    _DPTYPE = IntegerTypeInformation

    def __init__(
        self,
        dpcode: str,
        type_information: IntegerTypeInformation,
        dp_id: int | str | None = None,
    ) -> None:
        """Init DPCodeIntegerWrapper."""
        super().__init__(dpcode, type_information, dp_id)
        self.native_unit = type_information.unit
        self.min_value = self.type_information.scale_value(type_information.min)
        self.max_value = self.type_information.scale_value(type_information.max)
        self.value_step = self.type_information.scale_value(
            type_information.step
        )


class DPCodeJsonWrapper[T = dict[str, Any]](
    DPCodeTypeInformationWrapper[JsonTypeInformation, dict[str, Any], T]
):
    """Simple wrapper for JsonTypeInformation values."""

    _DPTYPE = JsonTypeInformation


class DPCodeRawWrapper[T = bytes](
    DPCodeTypeInformationWrapper[RawTypeInformation, bytes, T]
):
    """Simple wrapper for RawTypeInformation values."""

    _DPTYPE = RawTypeInformation


class DPCodeStringWrapper[T = str](
    DPCodeTypeInformationWrapper[StringTypeInformation, str, T]
):
    """Simple wrapper for StringTypeInformation values."""

    _DPTYPE = StringTypeInformation


class RawDPWrapper(DPCodeWrapper[Any]):
    """Wrapper for a DP with no cloud spec (localtuya fallback).

    Entities are config-driven by DP id and may reference DPs the cloud
    spec does not describe. This wrapper reads/writes the raw dp_id-keyed
    status value directly, without type conversion.
    """

    # Number bounds are unknown without a spec; entities fall back to their
    # configured min/max/step defaults when these are None.
    min_value: float | None = None
    max_value: float | None = None
    value_step: float | None = None

    def __init__(self, dp_id: int | str) -> None:
        """Init RawDPWrapper."""
        super().__init__(dpcode=str(dp_id), dp_id=dp_id)

    def skip_update(
        self,
        device: Any,
        updated_status_properties: list[str],
        dp_timestamps: dict[str, int] | None = None,
    ) -> bool:
        """Never skip state writes for a spec-less DP.

        dpcodes cannot be mapped for an unknown DP, so there is nothing to
        compare against; always reflect the device state.
        """
        return False

    def _convert_value_to_raw_value(self, device: Any, value: Any) -> Any:
        """No conversion is available without a spec; pass through."""
        return value


class BitmapMaskWrapper(DPCodeWrapper[bool]):
    """Wrapper that applies a configured bitmask to a bitmap DP.

    Localtuya entities can configure a ``bitmap_mask`` to read/write a
    single bit (or bits) of a raw bitmap DP. This wraps the inner wrapper
    (cloud spec or RawDPWrapper) and applies the mask on every read/write.
    """

    def __init__(self, inner: DPCodeWrapper[Any], mask: bytes) -> None:
        """Init BitmapMaskWrapper."""
        super().__init__(dpcode=inner.dpcode, dp_id=inner.dp_id)
        self._inner = inner
        self._mask = mask

    def _bitmap_value(self, device: Any) -> bytes:
        """Return the current DP value as bytes, zero-padded to mask length."""
        value = device.status.get(str(self.dp_id))
        if not isinstance(value, bytes):
            value = b""
        mask_len = len(self._mask)
        return value.ljust(mask_len, b"\x00")[:mask_len]

    def read_device_status(self, device: Any) -> bool:
        """Return True if any masked bit is set."""
        return any(
            v & m
            for v, m in zip(self._bitmap_value(device), self._mask, strict=True)
        )

    def _convert_value_to_raw_value(self, device: Any, value: bool) -> bytes:
        """Apply the mask to the current DP value for on/off writes."""
        return bytes(
            (v | m) if value else (v & ~m)
            for v, m in zip(self._bitmap_value(device), self._mask, strict=True)
        )

    def skip_update(
        self,
        device: Any,
        updated_status_properties: list[str],
        dp_timestamps: dict[str, int] | None = None,
    ) -> bool:
        """Delegate skip decisions to the inner wrapper."""
        return self._inner.skip_update(
            device, updated_status_properties, dp_timestamps
        )


_WRAPPERS_BY_DPTYPE: dict[DPType, type[DPCodeWrapper]] = {
    DPType.BITMAP: DPCodeBitmapWrapper,
    DPType.BOOLEAN: DPCodeBooleanWrapper,
    DPType.ENUM: DPCodeEnumWrapper,
    DPType.INTEGER: DPCodeIntegerWrapper,
    DPType.JSON: DPCodeJsonWrapper,
    DPType.RAW: DPCodeRawWrapper,
    DPType.STRING: DPCodeStringWrapper,
}


def dp_wrapper_by_id(
    device: Any, dp_id: int | str | None, *, prefer_function: bool = False
) -> DPCodeWrapper | None:
    """Resolve a wrapper from a numeric DP id.

    Scans the device's status_range/function specs for an entry whose DP id
    matches, then builds the wrapper for the entry's DP type.  Returns None
    when the DP id is unknown or its type is not supported.
    """
    if dp_id is None:
        return None
    lookup_tuple = (
        (device.function, device.status_range)
        if prefer_function
        else (device.status_range, device.function)
    )
    for device_specs in lookup_tuple:
        for dpcode, spec in device_specs.items():
            if str(_spec_dp_id(spec)) != str(dp_id):
                continue
            if wrapper := dp_wrapper_by_code(device, dpcode):
                wrapper.dp_id = dp_id
                return wrapper
    return None


def dp_wrapper_by_code(
    device: Any, dpcode: str, *, prefer_function: bool = False
) -> DPCodeWrapper | None:
    """Resolve a wrapper for a dpcode from the device specs.

    Returns None when the dpcode is unknown or its type is not supported.
    """
    lookup_tuple = (
        (device.function, device.status_range)
        if prefer_function
        else (device.status_range, device.function)
    )
    for device_specs in lookup_tuple:
        if (spec := device_specs.get(dpcode)) is None:
            continue
        dptype = DPType.try_parse(_spec_type(spec))
        wrapper_cls = _WRAPPERS_BY_DPTYPE.get(dptype)
        if wrapper_cls is None:
            continue
        type_information = _build_type_information(wrapper_cls, dpcode, spec)
        if type_information is not None:
            return wrapper_cls(
                dpcode=dpcode,
                type_information=type_information,
                dp_id=_spec_dp_id(spec),
            )
    return None


def _spec_type(spec: Any) -> str | None:
    """Return the DP type string from a spec entry that is an object or a dict."""
    if isinstance(spec, dict):
        return spec.get("type")
    return getattr(spec, "type", None)


def _build_type_information(
    wrapper_cls: type[DPCodeTypeInformationWrapper],
    dpcode: str,
    spec: Any,
) -> TypeInformation | None:
    """Build the TypeInformation for a spec entry (object or dict)."""
    if isinstance(spec, dict):
        type_data = spec.get("values")
        report_type = spec.get("report_type")
    else:
        type_data = spec.values
        report_type = getattr(spec, "report_type", None)
    return wrapper_cls._DPTYPE._from_json(
        dpcode=dpcode,
        type_data=type_data,
        report_type=report_type,
    )