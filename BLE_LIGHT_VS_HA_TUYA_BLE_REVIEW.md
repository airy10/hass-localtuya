# BLE Light: localtuya-unified vs. ha_tuya_ble — Full Review

Review date: 2026-08-13
Scope: light color/brightness/white/color_temp/work_mode encoding over the Tuya BLE transport.

References:
- Ours: `custom_components/localtuya/light.py`, `core/tuya_ble_lib/tuya_ble.py`, `core/transport/base.py`, `coordinator.py`
- Reference: `/Users/airy/Sources/airy/github/ha_tuya_ble/custom_components/tuya_ble/{light,devices,base}.py`, `tuya_ble/tuya_ble.py`

## Bottom line

After the BLE transport fixes (`MODE_COLOR_ALIASES`, v-channel brightness, s=0 white,
`white_mode_supported` capability refactor), the wire behavior for the `nvfrtxlq` strip is
**functionally identical to the reference**. The implementations differ mainly in *how* they
get there, and the reference contains several latent bugs that ours fixes.

## 1. Architecture

| | Ours | Reference |
|---|---|---|
| Light entity | `localtuya/light.py` (shared Ethernet + BLE) | `tuya_ble/light.py` (BLE only) |
| BLE library | vendored `core/tuya_ble_lib/tuya_ble.py` | `tuya_ble/tuya_ble.py` (same lineage) |
| Color type source | user-configured `CONF_COLOR_TYPE_DATA` (`ColorTypeData.from_config`) | **derived from cloud `colour_data` spec** (h/s/v min/max), fallback `DEFAULT_COLOR_TYPE_DATA_V2` for `dd` |
| Mode fallback | `WORK_MODE_FALLBACK` + aliases (`MODE_COLOR_ALIASES` etc.) | nvfrtxlq override via `values_overrides` — **broken** (see §7) |
| White support | capability-based `TuyaDevice.white_mode_supported` | none (work_mode never meaningfully compared, see §5) |

## 2. Color encoding — wire format (identical)

Both write the same two formats, selected by the same rule (`len(colour_data) > 12` → RGB-encoded, else HSV):

**12-char HSV (v2):** `"{:04x}{:04x}{:04x}".format(round(h), round(s), round(v))`

| | Ours (`__to_color_v2`, light.py:545) | Reference (light.py:689) |
|---|---|---|
| h | `hs[0]` (0-360) | `remap(h, 0, 360)` → cloud h range |
| s | `hs[1]*10` (0-1000) | `remap(s, 0, 100)` → cloud s range |
| v | `brightness` (raw 10-1000) | `remap(brightness, 0, 255)` → cloud v range |

**Worked example** — hs=(240,100), brightness=255:
- Ours: `00f0` + `03e8` + `03e8` = `00f003e803e8`
- Reference: h=240, s=1000, v=1000 → `00f003e803e8` — **byte-identical**.

**14-char RGB-encoded:** `"{:02x}{:02x}{:02x}{:04x}{:02x}{:02x}".format(r,g,b,h,s,v)`
- Ours (light.py:562): s=`hs[1]*255/100` (0-255), v=`brightness` (10-1000 — **overflows `{:02x}`**)
- Reference (light.py:680): s/v cloud-remapped (1-1000 — **also overflows**)

> ⚠️ **Shared latent bug**: in RGB-encoded mode, when s or v > 255 the `{:02x}` emits 3 hex
> digits (e.g. `3e8`), producing a 15-16 char string the decoder mis-parses (fixed offsets).
> Not applicable to the 12-char path used by the user's strip, but a real defect for
> RGB-encoded products with 0-1000 ranges.

## 3. Color decoding — identical formulas

| Format | Ours (light.py:594) | Reference (light.py:830) |
|---|---|---|
| 12-char | `wrap(color, 4)` → h, s/10, v | `[:4]`, `[4:8]`, `[8:]` → same |
| >12-char | `color[6:10]`, `[10:12]`, `[12:14]` | same offsets |

Only difference: ours applies `remap_h_to` only when user configured `color_type`; reference
always applies the cloud-derived `h_type.remap_value_to`.

## 4. Brightness — functionally equivalent

| | Ours | Reference |
|---|---|---|
| HS write | pre-mapped `map_range(0-255 → 10-1000)` → v-channel (light.py:642-654) | `v = remap_value_from(brightness)` 0-255 → 1-1000 (light.py:669) |
| HS read | `__from_color` sets `_brightness` from v, property maps back (light.py:369-374) | `color_data.brightness` (light.py:85-88) |
| Other modes | writes `bright_value` dp | writes `bright_value` dp only if no colour_data |

**The one real difference**: ours floors brightness at 10 (`DEFAULT_LOWER_BRIGHTNESS`),
the reference at 1. Practically invisible.

> 🔑 The `MODE_COLOR_ALIASES` fix matters here: the reference's `color_mode` is effectively
> *always* HS (see §5), so it always routes brightness to the v-channel. Ours *correctly*
> detects `is_color_mode` (US "color" spelling) and does the same.

## 5. Mode handling / work_mode — the structural difference

### Reference (accidentally-always-color)
`TuyaBLEDataPoint.value` (tuya_ble.py:134-136) returns the **raw int** for DT_ENUM — never
mapped to a string. So `status.get(work_mode) != WorkMode.WHITE` (light.py:819-823) is
**always True** → `color_mode` is **always HS**. Two consequences:
- white mode is never entered (and work_mode writes go through the broken enum mapping → **always 0**)
- `turn_on` always writes `WorkMode.COLOUR` (light.py:649-655) for any color/brightness change

### Ours (correctly string-mapped)
- `TuyaBLEDataPoint.value` (tuya_ble.py:141-162) maps DT_ENUM int → cloud string via `_enum_string_for_id`
- `is_color_mode` / `is_white_mode` / `is_scene_mode` / `is_music_mode` compare real strings incl. US spelling alias
- `supported_color_modes` gated on real capability (`white_mode_supported`)

> **Verdict**: ours is strictly more correct. The reference's "works" behavior for this strip
> is an accident of two compounding bugs.

## 6. Worked byte-level comparison (hs=(240,100) b=255)

| Command | Ours | Reference |
|---|---|---|
| power dp | `01` (DT_BOOL) | `01` |
| colour_data dp | `30 30 66 30 30 33 65 38 30 33 65 38` = `"00f003e803e8"` | identical |
| work_mode | `"color"` → index 0 → `00` (DT_ENUM) | `"colour"` → broken mapping → `00` |

**Both send work_mode = 0, identical colour_data bytes. White pick: both send s≈0 (v2), mode 0.**

## 7. Bugs in the reference (and whether we share them)

| Bug | Reference | Ours | Impact |
|---|---|---|---|
| `values_overrides.values` — missing `[key]` → `f.values` = bound method (tuya_ble.py:375) | active (nvfrtxlq override inert) | same code at our tuya_ble.py:408 — **dead**: `update_description` never called with overrides | reference's work_mode override silently does nothing |
| `values_defaults.values` — same bug + walrus precedence (`if f := ... and not f.values`) | active | same (dead) | latent |
| `_send_command` enum: `int_value = 0` default; `range.index(v) if v in range else None` → sends `None` → `int(None)` **TypeError** (devices.py:128-135) | crashes if value not in range | `_enum_index_for_id` never returns None, falls back to work-mode fallback | ref crashes on unknown enum |
| RGB-encoded s/v overflow `{:02x}` | shared | **shared** | see §2 |
| `color_mode` always HS (int vs StrEnum) | broken | fixed | ref can't detect white mode |
| `_send_command` reads only `function` (not `status_range`) → KeyError | edge | scans both | edge |
| brightness=0 in `turn_on` treated as missing (`if not (brightness := ...)`) | minor | clamps to lower | cosmetic |

## 8. Worth adopting from the reference

1. **Cloud-derived color type spec** (the biggest gap). The reference reads the device's
   actual `colour_data` function spec (`h/s/v` min/max from cloud JSON) at setup
   (light.py:564-586). For a device whose cloud says `h.max=100` (common on some strip
   families), the reference remaps 0-360→0-100 and writes correct values; ours sends raw
   0-360 → wrong colors. For the user's strip (cloud h=360, s/v=1000) it's a no-op (identity).
2. Reference's `turn_on` builds a `commands` list, one dp per packet — ours does the same via
   `set_dps` dict. Equivalent. No change needed.

## 9. Better in ours (keep)

- `_enum_string_for_id` / `_enum_index_for_id` correct string↔int round-trip + `WORK_MODE_FALLBACK` + `"white"→0`
- `MODE_COLOR_ALIASES` / `MODE_MUSIC_ALIASES` (US/UK spelling) — root cause of the brightness bug
- RAW/BITMAP → hex projection
- capability-based white (`white_mode_supported`) instead of hardcoded transport checks
- `map_range` clamps (reference `remap_value` doesn't)
- `DT_ENUM` packing `>B/>H/>I` — identical to reference

## 10. Actionable items

- [x] Implement cloud-derived `ColorTypeData` in `connection_made()` when `CONF_COLOR_TYPE_DATA` unset
- [x] Fix / remove the dead `update_description` `values_overrides.values` bug (tuya_ble.py:400-422)
- [x] Document the shared RGB-encoded overflow bug in `light.py`