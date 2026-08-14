# Wrapper Decorator Refactoring Spec

> **Status: IMPLEMENTED.** All phases complete; 110 platform tests + 20 new
> decorator unit tests pass. The decorators live in
> `core/dp_wrapper_decorators.py` and compose through the inner wrapper's
> public `read_device_status` / `get_update_commands` interface (not the
> private `_read_dpcode_value` hooks shown in the sketches below).

## Problem Statement

Core HA tuya pushes all conversion logic into wrapper classes. Entity methods are thin one-liner calls (`_read_wrapper` / `_async_send_wrapper_updates`). LocalTuya does the opposite: entities handle conversion (DictSelector maps, percentage scaling, timed cover math, string color encoding, unit/precision), wrappers are raw pass-through. This creates two implementations for the same device functionality.

**Goal**: Entity classes become functionally identical to core - as close as possible for the implementation (funcs, func code, etc). All conversion lives in wrapper decorators. Transport differences stay in the base class. Wrapper resolution stays config-driven (vs core's definition-driven).

## Architecture Gap Analysis

| Conversion | Core Wrapper | LocalTuya Current | Gap |
|------------|-------------|-------------------|-----|
| DictSelector (select, climate modes, humidifier modes, alarm modes) | `DPCodeEnumWrapper` (via `TypeInformation.range`) | Entity calls `DictSelector.to_ha()` / `to_tuya()` in property/methods | Entities do dict lookup; wrapper just reads raw |
| Percentage scaling (fan speed) | `FanSpeedIntegerWrapper` (remaps to 1..100) | Entity calls `percentage_to_ranged_value()` / `ranged_value_to_percentage()` | Entity does math; wrapper reads raw |
| Direction mapping (fan) | `FanDirectionEnumWrapper` (maps `forward/reverse` → `TuyaFanDirection`) | Entity compares raw value to config strings | Entity does string comparison; wrapper returns HA constant |
| Timed cover math (position) | `ControlBackModePercentageMappingWrapper` | Entity uses span_time-based timed mode (movement tracking); no 65535 math | Not applicable — localtuya timed covers track movement via span_time, not 65535 |
| Position inversion (cover) | `DPCodeInvertedPercentageWrapper` | Entity calls `100 - position` | Entity inverts; wrapper returns inverted |
| String color encoding (light v1/v2/base64) | `ColorDataWrapper` (JSON HSV) | Entity decodes base64/string, computes HSV | Entity decodes; wrapper returns HSV tuple |
| Temperature precision/unit (climate) | `IntegerTypeInformation` (scale) | Entity does `raw * precision` + `f_to_c`/`c_to_f` | Entity scales/converts; wrapper returns scaled |
| Unit conversion (climate) | Wrapper has `native_unit` | Entity checks `if self._current_temp_unit != self.temperature_unit` | Entity converts; wrapper returns native |
| Switch-only mode (climate) | `DefaultHVACModeWrapper` | Entity checks `self._switch_wrapper` in `hvac_mode` | Entity handles fallback; wrapper returns mode |
| Fan preset mode (humidifier) | `DPCodeEnumWrapper` | Entity converts via `DictSelector` | Entity converts; wrapper returns string |

## Wrapper Decorator Design

Decorators wrap an existing wrapper and add conversion in `read_device_status` / `get_update_commands`. Composable: `InversionWrapper(TimedCoverMathWrapper(RawDPWrapper("dp_1")))`.

**Implementation note**: the sketches below show decorators sub-classing
`DPCodeWrapper` with their own `dpcode`; the actual implementation instead
wraps an *inner* wrapper (``DecoratorWrapper.__init__(inner)``) and converts
one step before delegating through the inner wrapper's public
`read_device_status` / `get_update_commands`, which keeps them composable and
duck-typing friendly. The implemented set also includes `BrightnessWrapper`,
`ColorTempWrapper` and `HumidityCoefficientWrapper` (light + climate).

### 1. `DictSelectorWrapper`

Wraps raw value with `DictSelector.to_ha()` / `to_tuya()` conversion.

```python
class DictSelectorWrapper(DPCodeWrapper[str]):
    """Wraps raw DP value through a DictSelector for select/climate/humidifier modes."""

    def __init__(self, dpcode: str, options: DictSelector):
        super().__init__(dpcode)
        self._selector = options

    @property
    def options(self) -> list[str]:
        return self._selector.names

    def _read_dpcode_value(self, device) -> str | None:
        raw = super()._read_dpcode_value(device)
        if raw is not None:
            return self._selector.to_ha(raw, raw)
        return None

    def _convert_value_to_raw_value(self, device, value: str) -> str:
        return self._selector.to_tuya(value)
```

**Used by**: select (current_option), climate (hvac_mode, preset_mode, fan_mode, swing_mode), humidifier (mode), alarm_control_panel (mode).

### 2. `ScalingIntegerWrapper`

Wraps raw integer with min/max/step scaling (core's `IntegerTypeInformation` equivalent).

```python
class ScalingIntegerWrapper(DPCodeWrapper[int]):
    """Wraps raw integer DP with scaling (min/max/step/unit)."""

    def __init__(self, dpcode: str, min_value: float, max_value: float,
                 step: float = 1, unit: str | None = None, scale: int = 0):
        super().__init__(dpcode)
        self.min_value = min_value
        self.max_value = max_value
        self.value_step = step
        self.native_unit = unit
        self._scale = scale  # 10^scale divisor

    def _read_dpcode_value(self, device) -> int | None:
        raw = super()._read_dpcode_value(device)
        if raw is not None and self._scale:
            return round(raw / 10 ** self._scale)
        return raw

    def _convert_value_to_raw_value(self, device, value: int) -> int:
        if self._scale:
            return round(value * 10 ** self._scale)
        return value
```

**Used by**: fan (speed percentage), number (value), climate (target_temperature, target_humidity).

### 3. `PercentageWrapper`

Special case of `ScalingIntegerWrapper` for 0..100 percentage.

```python
class PercentageWrapper(DPCodeWrapper[int]):
    """Wraps raw integer DP as 0..100 percentage (with optional scaling)."""

    def __init__(self, dpcode: str, scale: int = 0):
        super().__init__(dpcode)
        self.min_value = 0
        self.max_value = 100
        self.value_step = 1
        self.native_unit = PERCENTAGE
        self._scale = scale

    def _read_dpcode_value(self, device) -> int | None:
        raw = super()._read_dpcode_value(device)
        if raw is not None and self._scale:
            return round(raw / 10 ** self._scale)
        return raw

    def _convert_value_to_raw_value(self, device, value: int) -> int:
        if self._scale:
            return round(value * 10 ** self._scale)
        return value
```

### 4. `InvertedPercentageWrapper`

Inverts 100 → 0, 0 → 100.

```python
class InvertedPercentageWrapper(PercentageWrapper):
    """Wraps percentage DP with inversion (100 - value)."""

    def _read_dpcode_value(self, device) -> int | None:
        raw = super()._read_dpcode_value(device)
        if raw is not None:
            return 100 - raw
        return None

    def _convert_value_to_raw_value(self, device, value: int) -> int:
        raw = super()._convert_value_to_raw_value(device, value)
        return 100 - raw
```

### 5. `InversionWrapper`

Inverts position: `value → max - value` (configurable max).

```python
class InversionWrapper(DPCodeWrapper[int]):
    """Inverts position value: position → max - position."""

    def __init__(self, dpcode: str, max_value: int = 100):
        super().__init__(dpcode)
        self._max = max_value

    def _read_dpcode_value(self, device) -> int | None:
        raw = super()._read_dpcode_value(device)
        if raw is not None:
            return self._max - raw
        return None

    def _convert_value_to_raw_value(self, device, value: int) -> int:
        return self._max - value
```

### 6. `TimedCoverMathWrapper`

Handles timed cover position math: position = round(val * 65535 / 100).

```python
class TimedCoverMathWrapper(DPCodeWrapper[int]):
    """Wraps timed cover DP: round(raw * 65535 / 100) for position."""

    def __init__(self, dpcode: str):
        super().__init__(dpcode)

    def _read_dpcode_value(self, device) -> int | None:
        raw = super()._read_dpcode_value(device)
        if raw is not None:
            return round(raw * 65535 / 100)
        return None

    def _convert_value_to_raw_value(self, device, value: int) -> int:
        return round(value * 100 / 65535)
```

### 7. `StringColorWrapper`

Handles v1/v2/base64 string color encoding (light).

```python
class StringColorWrapper(DPCodeWrapper[tuple[float, float, int]]):
    """Wraps string color DP: decodes base64/string to HS+brightness tuple."""

    def __init__(self, dpcode: str, color_type_data: ColorTypeData):
        super().__init__(dpcode)
        self._color_type_data = color_type_data

    def _read_dpcode_value(self, device) -> tuple[float, float, int] | None:
        raw = super()._read_dpcode_value(device)
        if raw is None:
            return None
        return self._decode_color(raw)

    def _convert_value_to_raw_value(self, device, value: tuple[float, float, int]) -> str:
        return self._encode_color(value)

    def _decode_color(self, raw: str) -> tuple[float, float, int] | None:
        """Decode base64/string to (hs_hue, hs_saturation, brightness)."""
        # V1: base64 decode → unpack 4 bytes (H, S, V, ?)
        # V2: base64 decode → unpack 7 bytes (H, S, V, ?, ?, ?, ?)
        # String: "H,S,V" or hex
        # Returns (hue, saturation, brightness)
        ...

    def _encode_color(self, value: tuple[float, float, int]) -> str:
        """Encode (hue, saturation, brightness) to base64/string."""
        # Returns base64-encoded string matching color_type_data format
        ...
```

### 8. `InvertedBooleanWrapper`

Inverts boolean: True → False, False → True.

```python
class InvertedBooleanWrapper(DPCodeWrapper[bool]):
    """Inverts boolean DP value."""

    def _read_dpcode_value(self, device) -> bool | None:
        raw = super()._read_dpcode_value(device)
        return not raw if raw is not None else None

    def _convert_value_to_raw_value(self, device, value: bool) -> bool:
        return not value
```

### 9. `ClimateTempWrapper`

Handles Celsius revert + precision rounding.

```python
class ClimateTempWrapper(DPCodeWrapper[float]):
    """Wraps temperature DP: Celsius revert + precision rounding."""

    def __init__(self, dpcode: str, precision: int = 1, celsius_revert: bool = False):
        super().__init__(dpcode)
        self._precision = precision
        self._celsius_revert = celsius_revert

    def _read_dpcode_value(self, device) -> float | None:
        raw = super()._read_dpcode_value(device)
        if raw is None:
            return None
        if self._celsius_revert:
            raw = raw / 10
        return round(raw, self._precision)

    def _convert_value_to_raw_value(self, device, value: float) -> int:
        if self._celsius_revert:
            return round(value * 10)
        return round(value)
```

## Platform-by-Platform Implementation Plan

### Phase 1: Proof of Concept — select.py

**Current state**: Entity does `self._options.to_ha(value, value)` in `current_option`, `self._options.to_tuya(option)` in `async_select_option`.

**Target**: Entity becomes thin like core:
```python
@property
def current_option(self) -> str | None:
    return self._read_wrapper(self._dpcode_wrapper)

async def async_select_option(self, option: str) -> None:
    await self._async_send_wrapper_updates(self._dpcode_wrapper, option)
```

**Changes**:
1. In `__init__`: wrap `dp_wrapper_by_id(device, self._dp_id)` with `DictSelectorWrapper(dpcode, DictSelector(options))`.
2. Remove `status_updated` (wrapper handles reads).
3. Remove `_state_friendly` cache.
4. Remove `entity_default_value` override.

**Test impact**: 12+1 tests (6 unit, 6 integration, 1 wrapper). Update delegation test to use new wrapper.

### Phase 2: simple.py — bitmap masks

**Current state**: `status_updated` reads bitmap values for 3-4 switch options. Entities call `read_dp_value(bitmap_wrapper)`.

**Target**: No changes needed (BitmapMaskWrapper already handles conversion). Just verify no `status_updated` overrides.

### Phase 3: fan.py — percentage + direction

**Current state**: `percentage` property does `ranged_value_to_percentage(self._speed_range, speed)`. `async_set_percentage` does `percentage_to_ranged_value`. `current_direction` compares raw to config strings. `status_updated` caches `_percentage`/`_direction`.

**Target**:
1. Wrap speed DP with `FanSpeedPercentageWrapper(dpcode, min, max)` that does `percentage_to_ranged_value` / `ranged_value_to_percentage` in its methods.
2. Wrap direction DP with `DictSelectorWrapper(dpcode, DictSelector({fwd: "forward", rev: "reverse"}))` or a dedicated `FanDirectionWrapper` that maps raw → HA constant.
3. Remove `status_updated` override (remove caching of `_percentage`, `_direction`, `_oscillating`).
4. Remove `supported_features` override (features determined by which wrappers are non-None).

**Wrapper details**:
- `FanSpeedPercentageWrapper`: wraps `RawDPWrapper(dpcode)` → reads raw int → `ranged_value_to_percentage(range, int)` → returns int 0..100. Writes: `percentage_to_ranged_value(range, value)` → returns raw int.
- `FanDirectionWrapper`: wraps raw → config string lookup → returns `DIRECTION_FORWARD`/`DIRECTION_REVERSE`. Writes: reverse lookup.

### Phase 4: light.py — string color encoding

**Current state**: `hs_color` decodes base64/hex string via `__from_color*`;
`brightness` reads the brightness DP or the HS color v-value;
`color_temp_kelvin` uses `_color_temp_reverse` + `map_range`; `status_updated`
caches `_hs`, `_color_temp`, `_brightness`.

**Target** (implemented):
1. Wrap color DP with `StringColorWrapper(inner, color_type_data, upper_brightness, use_raw)` that decodes/encodes v1/v2/base64.
2. Wrap brightness DP with `BrightnessWrapper(inner, lower, upper)` (device range ↔ 0..255).
3. Wrap color_temp DP with `ColorTempWrapper(inner, min_kelvin, max_kelvin, lower, upper, reverse)`.
4. Remove `status_updated` override; `hs_color`/`brightness`/`color_temp_kelvin`/`effect` read live through the wrappers.
5. Remove `_color_temp_reverse` (handled by `ColorTempWrapper`).

**Note**: Light is the most complex platform; scene/effect and work-mode
classification stay config-driven in the entity.

### Phase 5: cover.py — position inversion

**Current state** (corrected): localtuya cover.py has **no** 65535 math. Its
timed mode tracks movement with `span_time` (a state machine in the entity),
and position inversion is a simple `100 - position` on the set-position
write. `status_updated` is genuine state-machine logic (opening/closing/stop).

**Target** (implemented):
1. Wrap set-position DP with `InvertedPercentageWrapper(inner)` when
   `position_inverted` is set, so `async_set_cover_position` no longer does
   `100 - position`.
2. `status_updated` stays (movement tracking is genuine caching, not a
   removable conversion).

**Core reference**: `DPCodeInvertedPercentageWrapper` does the inversion.

### Phase 6: climate.py — DictSelector + unit/precision

**Current state**: `hvac_mode` calls `DictSelector.to_ha()`. `preset_mode` calls `DictSelector.to_ha()`. `fan_mode` calls `DictSelector.to_ha()`. `swing_mode` calls `DictSelector.to_ha()`. `target_temperature` does Celsius revert + precision rounding. Unit conversion in `current_temperature`/`target_temperature`.

**Target**:
1. Wrap hvac_mode DP with `DictSelectorWrapper(dpcode, hvac_mode_selector)`.
2. Wrap preset_mode DP with `DictSelectorWrapper(dpcode, preset_mode_selector)`.
3. Wrap fan_mode DP with `DictSelectorWrapper(dpcode, fan_mode_selector)`.
4. Wrap swing_mode DP with `DictSelectorWrapper(dpcode, swing_mode_selector)`.
5. Wrap target_temperature DP with `ClimateTempWrapper(dpcode, precision, celsius_revert)`.
6. Remove `status_updated` override (caches `_target_temperature`, `_hvac_mode`, `_preset_mode`).

**Core reference**: `DefaultHVACModeWrapper`, `DefaultPresetModeWrapper`, `SwingModeCompositeWrapper`.

### Phase 7: humidifier.py — mode DictSelector

**Current state**: `mode` property converts raw to friendly name via `DictSelector`. Already fixed in this session (raw → `_available_modes.to_ha()`).

**Target**: Wrap mode DP with `DictSelectorWrapper(dpcode, mode_selector)`. Remove `DictSelector` from `__init__` (wrapper provides options). Remove `_available_modes` attribute (wrapper has options).

### Phase 8: vacuum.py — status lists

**Current state** (corrected): vacuum has no battery DP. Its `activity` is a
state-machine classification across the configured idle/docked/returning/
paused/stop status lists (genuine entity logic), and `fan_speed` already
delegates through a wrapper.

**Target** (implemented): make `fan_speed` fully thin (drop the `_fan_speed`
cache fallback). The status classification and extra-state-attributes stay in
`status_updated` — they are not a single-DP conversion.

### Phase 9: Remaining platforms

- `alarm_control_panel.py` (implemented): Wrap mode DP with `DictSelectorWrapper`; remove `status_updated`.
- `water_heater.py` (implemented): Wrap mode DP with `DictSelectorWrapper` and temps with `ClimateTempWrapper`; replace `status_updated` with live wrapper reads.
- `number.py`: Already thin (delegates to wrapper; config scaling/offset stays config-driven).
- `binary_sensor.py`: `state_on` string matching + reset timer are config-driven; the wrapper only gates `skip_update`. No conversion to move.
- `sensor.py`: base64 phase sub-sensors + config scaling/offset + icons are config-driven; keep `status_updated`.
- `siren.py`: `state_on` matching is config-driven; `is_on` already reads the wrapper for bool DPs. No conversion to move.
- `valve.py`: Already thin (`is_closed` reads wrapper; open/close send wrapper updates).
- `lock.py`: `_attr_is_locked`/`_attr_is_jammed` derive from `lock_state_dp`/`jammed_dp` (config-driven); left as-is.
- `remote.py`: `status_updated` drives the remote command state machine; left as-is.
- `button.py`: No changes needed (action only).

## Test Strategy

1. **Unit tests**: Each wrapper decorator gets its own test file (`tests/test_dict_selector_wrapper.py`, etc.). Test `read_device_status` (raw → converted) and `get_update_commands` (converted → raw).
2. **Platform delegation tests**: Update existing tests to verify thin entity calls (no conversion in entity methods).
3. **Integration tests**: Verify end-to-end with mock devices. Ensure HA state matches expected values.
4. **Regression check**: Run full test suite after each platform refactor.

## Implementation Order

1. select.py (proof of concept) — DictSelectorWrapper
2. simple.py — verify BitmapMaskWrapper (no changes needed)
3. fan.py — FanSpeedPercentageWrapper, FanDirectionWrapper
4. light.py — StringColorWrapper (most complex)
5. cover.py — TimedCoverMathWrapper, InversionWrapper
6. climate.py — DictSelectorWrapper (multiple), ClimateTempWrapper
7. humidifier.py — DictSelectorWrapper
8. vacuum.py — DictSelectorWrapper, PercentageWrapper
9. Remaining platforms (binary_sensor, sensor, number, siren, valve, alarm_control_panel, button)

## Success Criteria

After refactoring:
- Entity method bodies are one-liner `_read_wrapper` / `_async_send_wrapper_updates` calls (matching core).
- No `status_updated` overrides remain (except genuine caching needs).
- No `DictSelector.to_ha()` / `to_tuya()` calls in entity code.
- No `percentage_to_ranged_value` / `ranged_value_to_percentage` in entity code.
- No string color encode/decode in entity code (owned by `StringColorWrapper`).
- No position inversion (`100 - position`) in the cover write path (owned by `InvertedPercentageWrapper`).
- No `f_to_c`/`c_to_f`/precision math in entity code (owned by `ClimateTempWrapper`).
- All 110+ tests pass.
- Wrapper decorators are composable and independently testable.
