"""Product-id keyed quirks registry.

Mirrors core tuya's ``QuirksRegistry`` + ``DeviceQuirk``
(``tuya_device_handlers/registry.py`` + ``builder/device_quirk.py``): a registry
keyed by ``product_id`` that patches a device's cloud spec (``function`` /
``status_range`` / ``category``) before entity wrappers are resolved, so that
buggy or missing DP metadata in Tuya's catalog is corrected per product.

A quirk *is* a patch to the cloud device description: the datapoint-patching
quirks below are applied to ``TuyaDevice.function``/``status_range`` (see
coordinator.py), which is the same surface ``dp_wrapper_by_code`` /
``definitions.resolve`` read. We cannot fix Tuya's catalog on their servers, so
the fixes live here as versioned, per-product overrides — the same shape core
uses, so future core quirks port 1:1.

The datapoint-patching quirks are ported from the pinned
``tuya-device-handlers`` package's ``devices/`` tree (one file per product).
Deliberate omissions (see ARCHITECTURE_ALIGNMENT_CORE_TUYA.md §7.9):
  - ``override_dpid_type_information_cls`` (``InvertedIntegerTypeInformationEx``)
    is not ported: core applies it to curtain/blind motors to cancel its
    *default* position inversion, but localtuya cover inversion is config-driven
    (``position_inverted``), so those cl/clkg quirks are no-ops for us.
  - ``map_feeder_schedules_wrapper`` (pet-feeder meal plan) is not ported: we
    have no feeder-schedule service.

Our per-product entity mappings live in ``core/mappings.py`` (``MAPPINGS``);
``button_switch_dp`` covers the Fingerbot physical-button DP.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntFlag
from typing import Any, Self

from ..const import DPType


class DPMode(IntFlag):
    """Which direction a datapoint is valid in (mirrors core ``const.DPMode``)."""

    READ = 1
    WRITE = 2


@dataclass
class DatapointDefinition:
    """A quirk-added/overridden datapoint definition (mirrors core)."""

    dpid: int
    dpcode: str
    dptype: DPType
    values: dict[str, Any]
    read: bool
    write: bool
    report_type: str | None = None

    def to_spec(self) -> dict[str, Any]:
        """Return a dpcode-keyed spec entry compatible with ``dp_wrappers``.

        ``dp_wrapper_by_code`` accepts both dict specs (Ethernet) and object
        specs (BLE), so a plain dict with ``code``/``dp_id``/``type``/``values``
        works for both transports.
        """
        spec: dict[str, Any] = {
            "code": self.dpcode,
            "dp_id": self.dpid,
            "type": self.dptype,
            "values": self.values,
        }
        if self.report_type is not None:
            spec["report_type"] = self.report_type
        return spec


class DeviceQuirk:
    """Behavior overrides for a specific product_id."""

    def __init__(self, button_switch_dp: int | None = None) -> None:
        """Initialize the quirk.

        ``button_switch_dp`` is kept as a constructor kwarg for the Fingerbot
        table (which predates the fluent builder); spec-patching quirks use the
        builder methods below.
        """
        self.button_switch_dp = button_switch_dp
        self.category_override: str | None = None
        self.manufacturer: str | None = None
        self.model: str | None = None
        self.model_id: str | None = None
        self._applies_to: str | None = None
        self._datapoint_definitions: dict[str, DatapointDefinition | None] = {}

    def applies_to(
        self,
        *,
        product_id: str,
        manufacturer: str | None = None,
        model: str | None = None,
        model_id: str | None = None,
    ) -> Self:
        """Set the device type the quirk applies to."""
        self._applies_to = product_id
        self.manufacturer = manufacturer
        self.model = model
        self.model_id = model_id
        return self

    def override_category(self, category: str) -> Self:
        """Set the category override applied to the device spec."""
        self.category_override = category
        return self

    def add_dpid_enum(
        self, *, dpid: int, dpcode: str, dpmode: DPMode, enum_range: list[str]
    ) -> Self:
        """Add/override a datapoint Enum definition."""
        self._datapoint_definitions[dpcode] = DatapointDefinition(
            dpid=dpid,
            dpcode=dpcode,
            dptype=DPType.ENUM,
            values={"range": list(enum_range)},
            read=bool(dpmode & DPMode.READ),
            write=bool(dpmode & DPMode.WRITE),
        )
        return self

    def add_dpid_integer(
        self,
        *,
        dpid: int,
        dpcode: str,
        dpmode: DPMode,
        unit: str,
        min: int,  # noqa: A002  # pylint: disable=redefined-builtin
        max: int,  # noqa: A002  # pylint: disable=redefined-builtin
        scale: int,
        step: int,
        report_type: str | None = None,
    ) -> Self:
        """Add/override a datapoint Integer definition."""
        self._datapoint_definitions[dpcode] = DatapointDefinition(
            dpid=dpid,
            dpcode=dpcode,
            dptype=DPType.INTEGER,
            values={
                "unit": unit,
                "min": int(min),
                "max": int(max),
                "scale": int(scale),
                "step": int(step),
            },
            read=bool(dpmode & DPMode.READ),
            write=bool(dpmode & DPMode.WRITE),
            report_type=report_type,
        )
        return self

    def add_dpid_boolean(self, *, dpid: int, dpcode: str, dpmode: DPMode) -> Self:
        """Add/override a datapoint Boolean definition."""
        self._datapoint_definitions[dpcode] = DatapointDefinition(
            dpid=dpid,
            dpcode=dpcode,
            dptype=DPType.BOOLEAN,
            values={},
            read=bool(dpmode & DPMode.READ),
            write=bool(dpmode & DPMode.WRITE),
        )
        return self

    def add_dpid_bitmap(
        self, *, dpid: int, dpcode: str, dpmode: DPMode, label_range: list[str]
    ) -> Self:
        """Add/override a datapoint Bitmap definition."""
        self._datapoint_definitions[dpcode] = DatapointDefinition(
            dpid=dpid,
            dpcode=dpcode,
            dptype=DPType.BITMAP,
            values={"label": list(label_range)},
            read=bool(dpmode & DPMode.READ),
            write=bool(dpmode & DPMode.WRITE),
        )
        return self

    def remove_dpid(self, *, dpid: int, dpcode: str) -> Self:
        """Remove a datapoint definition (a ``None`` marker)."""
        self._datapoint_definitions[dpcode] = None
        return self

    def register(self, registry: "QuirksRegistry") -> None:
        """Register the quirk in the registry."""
        if self._applies_to is None:
            msg = "DeviceQuirk does not have an applies_to condition"
            raise ValueError(msg)
        registry.register(self._applies_to, self)

    def patch_function(self, function: dict[str, Any]) -> dict[str, Any]:
        """Return ``function`` with write-side quirk definitions applied."""
        return self._patch_specs(function, write=True)

    def patch_status_range(self, status_range: dict[str, Any]) -> dict[str, Any]:
        """Return ``status_range`` with read-side quirk definitions applied."""
        return self._patch_specs(status_range, write=False)

    def patched_category(self, category: str | None) -> str | None:
        """Return the category with the quirk's override applied."""
        return self.category_override if self.category_override else category

    def _patch_specs(
        self, specs: dict[str, Any], *, write: bool
    ) -> dict[str, Any]:
        """Apply this quirk's datapoint definitions to a spec surface.

        For each definition: remove the dpcode (explicit ``remove_dpid``),
        add/override it (when it applies to this read/write surface), or drop
        it (when it applies only to the other surface). Mirrors core's
        ``initialise_device``.
        """
        if not self._datapoint_definitions:
            return specs
        result = dict(specs)
        for dpcode, definition in self._datapoint_definitions.items():
            if definition is None:
                result.pop(dpcode, None)
            elif definition.write if write else definition.read:
                result[dpcode] = definition.to_spec()
            else:
                result.pop(dpcode, None)
        return result


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

QUIRKS_REGISTRY = QuirksRegistry()

# --- Fingerbot physical-button DP quirks -------------------------------------
for _product_id, _dp_id in FINGERBOT_SWITCH_DP.items():
    QUIRKS_REGISTRY.register(_product_id, DeviceQuirk(button_switch_dp=_dp_id))

# --- Ported core spec-patching quirks ----------------------------------------
# One entry per product, ported from tuya_device_handlers/devices/*.py.
# (cl/clkg InvertedIntegerTypeInformationEx quirks and the cwwsq feeder quirk
# are intentionally omitted — see module docstring.)

# bh — Tuya smart kettle (Anko LD-K3068): expand temp_setting_quick_c enum.
(
    DeviceQuirk()
    .applies_to(
        product_id="dft4ebatvon3ha5s",
        manufacturer="Anko",
        model="Smart kettle",
        model_id="LD-K3068",
    )
    .add_dpid_enum(
        dpid=4,
        dpcode="temp_setting_quick_c",
        dpmode=DPMode.READ | DPMode.WRITE,
        enum_range=["80", "85", "90", "95", "100"],
    )
    .register(QUIRKS_REGISTRY)
)

# cl — A-OK AM45 Plus Wi-Fi tubular motor: suppress stale percent_state.
(
    DeviceQuirk()
    .applies_to(
        product_id="b9oa3zocv4qq47iy",
        manufacturer="A-OK",
        model="Tubular motor",
        model_id="AM45 Plus Wi-Fi",
    )
    .remove_dpid(dpid=3, dpcode="percent_state")
    .register(QUIRKS_REGISTRY)
)

# cs — DH-24 Nexi ION UV Wifi dehumidifier: expose indoor humidity/temp.
(
    DeviceQuirk()
    .applies_to(product_id="uhtamgih7kkdcqtx")
    .add_dpid_integer(
        dpid=3,
        dpcode="humidity_indoor",
        dpmode=DPMode.READ,
        unit="%",
        min=0,
        max=100,
        scale=0,
        step=1,
    )
    .add_dpid_integer(
        dpid=103,
        dpcode="temp_indoor",
        dpmode=DPMode.READ,
        unit="°C",
        min=-20,
        max=60,
        scale=0,
        step=1,
    )
    .register(QUIRKS_REGISTRY)
)

# cz — metered sockets: cloud declares scale=0 for deci-watt/deci-volt DPs.
(
    DeviceQuirk()
    .applies_to(
        product_id="eyEYwtdx9VhexxLW",
        manufacturer="Gosund",
        model="Smart Socket",
        model_id="SP111",
    )
    .add_dpid_integer(
        dpid=5, dpcode="cur_power", dpmode=DPMode.READ, unit="W",
        min=0, max=50000, scale=1, step=1,
    )
    .add_dpid_integer(
        dpid=6, dpcode="cur_voltage", dpmode=DPMode.READ, unit="V",
        min=0, max=3000, scale=1, step=1,
    )
    .register(QUIRKS_REGISTRY)
)

(
    DeviceQuirk()
    .applies_to(product_id="QH3oyDNHKw9c1irH")
    .add_dpid_integer(
        dpid=5, dpcode="cur_power", dpmode=DPMode.READ, unit="W",
        min=0, max=50000, scale=1, step=1,
    )
    .add_dpid_integer(
        dpid=6, dpcode="cur_voltage", dpmode=DPMode.READ, unit="V",
        min=0, max=2500, scale=1, step=1,
    )
    .register(QUIRKS_REGISTRY)
)

(
    DeviceQuirk()
    .applies_to(
        product_id="qxJSyTLEtX5WrzA9",
        manufacturer="GHome",
        model="Mini Smart Plug",
        model_id="WP3",
    )
    .add_dpid_integer(
        dpid=5, dpcode="cur_power", dpmode=DPMode.READ, unit="W",
        min=0, max=50000, scale=1, step=1,
    )
    .add_dpid_integer(
        dpid=6, dpcode="cur_voltage", dpmode=DPMode.READ, unit="V",
        min=0, max=3000, scale=1, step=1,
    )
    .register(QUIRKS_REGISTRY)
)

(
    DeviceQuirk()
    .applies_to(
        product_id="wifvoilfrqeo6hvu",
        manufacturer="Gosund",
        model="Smart socket",
        model_id="EP2",
    )
    .add_dpid_integer(
        dpid=3, dpcode="add_ele", dpmode=DPMode.READ, unit="kWh",
        min=0, max=500000, scale=3, step=1, report_type="sum",
    )
    .add_dpid_integer(
        dpid=5, dpcode="cur_power", dpmode=DPMode.READ, unit="W",
        min=0, max=50000, scale=1, step=1,
    )
    .add_dpid_integer(
        dpid=6, dpcode="cur_voltage", dpmode=DPMode.READ, unit="V",
        min=0, max=5000, scale=1, step=1,
    )
    .register(QUIRKS_REGISTRY)
)

# fs — Comfort Zone Tower Fan (CZTF423S): expand mode/countdown enums.
(
    DeviceQuirk()
    .applies_to(
        product_id="xwv3jifdbhbolgh3",
        manufacturer="Comfort Zone",
        model="Tower Fan",
        model_id="CZTF423S",
    )
    .add_dpid_enum(
        dpid=2,
        dpcode="mode",
        dpmode=DPMode.READ | DPMode.WRITE,
        enum_range=["normal", "nature", "sleep"],
    )
    .add_dpid_enum(
        dpid=22,
        dpcode="countdown_set",
        dpmode=DPMode.READ | DPMode.WRITE,
        enum_range=[
            "cancel", "1h", "2h", "3h", "4h", "5h", "6h",
            "7h", "8h", "9h", "10h", "11h", "12h",
        ],
    )
    .register(QUIRKS_REGISTRY)
)

# kt — Della mini-split: force Fahrenheit temp_set; drop redundant temp_set_f.
(
    DeviceQuirk()
    .applies_to(product_id="hw50w7qvxluhslkk")
    .add_dpid_integer(
        dpid=2,
        dpcode="temp_set",
        dpmode=DPMode.READ | DPMode.WRITE,
        unit="℉",
        min=160,
        max=880,
        scale=1,
        step=5,
    )
    .remove_dpid(dpid=136, dpcode="temp_set_f")
    .register(QUIRKS_REGISTRY)
)

# tdq — temperature/humidity sensors: expose undocumented readings.
(
    DeviceQuirk()
    .applies_to(product_id="datzwoplui1zao16")
    .add_dpid_enum(
        dpid=20, dpcode="temp_unit_convert",
        dpmode=DPMode.READ | DPMode.WRITE, enum_range=["c", "f"],
    )
    .add_dpid_integer(
        dpid=27, dpcode="temp_current", dpmode=DPMode.READ, unit="℃",
        min=-200, max=600, scale=1, step=1,
    )
    .add_dpid_integer(
        dpid=46, dpcode="humidity_value", dpmode=DPMode.READ, unit="%",
        min=0, max=100, scale=0, step=1,
    )
    .register(QUIRKS_REGISTRY)
)

# tdq — contact sensor: re-categorize as door/window contact and expose DPs.
(
    DeviceQuirk()
    .applies_to(product_id="p6sqiuesvhmhvv4f")
    .override_category("mcs")
    .add_dpid_boolean(
        dpid=101, dpcode="doorcontact_state", dpmode=DPMode.READ,
    )
    .add_dpid_enum(
        dpid=102, dpcode="battery_state", dpmode=DPMode.READ,
        enum_range=["low", "middle", "high"],
    )
    .register(QUIRKS_REGISTRY)
)

(
    DeviceQuirk()
    .applies_to(product_id="x3o8epevyeo3z3oa")
    .add_dpid_enum(
        dpid=20, dpcode="temp_unit_convert",
        dpmode=DPMode.READ | DPMode.WRITE, enum_range=["c", "f"],
    )
    .add_dpid_integer(
        dpid=27, dpcode="temp_current", dpmode=DPMode.READ, unit="℃",
        min=-200, max=600, scale=1, step=1,
    )
    .add_dpid_integer(
        dpid=46, dpcode="humidity_value", dpmode=DPMode.READ, unit="%",
        min=0, max=100, scale=0, step=1,
    )
    .add_dpid_enum(
        dpid=101, dpcode="battery_state", dpmode=DPMode.READ,
        enum_range=["low", "middle", "high"],
    )
    .register(QUIRKS_REGISTRY)
)

(
    DeviceQuirk()
    .applies_to(product_id="xeagimantb7d7apb")
    .add_dpid_enum(
        dpid=20, dpcode="temp_unit_convert",
        dpmode=DPMode.READ | DPMode.WRITE, enum_range=["c", "f"],
    )
    .add_dpid_integer(
        dpid=27, dpcode="temp_current", dpmode=DPMode.READ, unit="℃",
        min=-200, max=600, scale=1, step=1,
    )
    .add_dpid_integer(
        dpid=46, dpcode="humidity_value", dpmode=DPMode.READ, unit="%",
        min=0, max=100, scale=0, step=1,
    )
    .add_dpid_enum(
        dpid=101, dpcode="battery_state", dpmode=DPMode.READ,
        enum_range=["low", "middle", "high"],
    )
    .register(QUIRKS_REGISTRY)
)

# wk — thermostats: expand/repair the mode enum.
(
    DeviceQuirk()
    .applies_to(product_id="cpmgn2cf")
    .add_dpid_enum(
        dpid=4, dpcode="mode", dpmode=DPMode.READ | DPMode.WRITE,
        enum_range=[
            "holiday", "auto", "manual", "comfort", "eco", "BOOST", "temp_auto",
        ],
    )
    .register(QUIRKS_REGISTRY)
)

(
    DeviceQuirk()
    .applies_to(product_id="if6pqia2gbtvqa6l")
    .add_dpid_enum(
        dpid=2, dpcode="mode", dpmode=DPMode.READ | DPMode.WRITE,
        enum_range=["auto", "home"],
    )
    .register(QUIRKS_REGISTRY)
)

(
    DeviceQuirk()
    .applies_to(
        product_id="ucf09xuve67adcp4",
        manufacturer="Warmtec",
        model="Thermostat",
        model_id="T510",
    )
    .add_dpid_enum(
        dpid=2, dpcode="mode", dpmode=DPMode.READ | DPMode.WRITE,
        enum_range=["auto", "comfort", "eco", "holiday"],
    )
    .register(QUIRKS_REGISTRY)
)

# wsdcg — Tem&Hum sensor with probe: expose external temperature.
(
    DeviceQuirk()
    .applies_to(product_id="m7kacaxrxbxeegfs")
    .add_dpid_integer(
        dpid=101, dpcode="ext_temp", dpmode=DPMode.READ, unit="℃",
        min=-200, max=1000, scale=1, step=1,
    )
    .register(QUIRKS_REGISTRY)
)

# znnbq — WVC micro inverter: power_total reports watts with scale 3.
(
    DeviceQuirk()
    .applies_to(
        product_id="7bqwya0ydtz4q3ss",
        manufacturer="WVC",
        model="Micro inverter",
        model_id="WVC-800W",
    )
    .add_dpid_integer(
        dpid=10, dpcode="power_total", dpmode=DPMode.READ, unit="W",
        min=0, max=50000000, scale=3, step=1,
    )
    .register(QUIRKS_REGISTRY)
)
