# BLE Runtime Worklog — `ble-qrcode-auth` (active branch)

> **Branch:** `ble-qrcode-auth` — **PUSHED to `https://github.com/airy10/hass-localtuya.git`**
> The user's Home Assistant install pulls this branch **directly from GitHub**, so every fix
> must be committed AND pushed to take effect on the live system.
> **Updated:** 2026-08-13 (session continuing — do not lose this)

---

## 0. One-paragraph status

BLE devices now set up, connect, expose correct entities, and the user's music light
(`LGB102 蓝牙BK幻彩灯带 30点`, MAC `DC:23:4D:96:0A:40`, product `nvfrtxlq`, category `dd`)
turns on/off, and mode writes now succeed (device echoes mode `0`). **Remaining**: brightness
still has no visible effect because the device's cloud `work_mode` values use the **US
spelling `"color"`** while localtuya's canonical string is `"colour"` (UK) → `is_color_mode`
is always False → brightness is routed to `bright_value` (dp 3), which the device never
echoes/applies. Fixed with `MODE_COLOR_ALIASES = ("color",)` (see §5); **pending live
verification** by the user on the next restart (§7). Saturation appears stuck at max on the
strip (device ignores the `s` channel of `colour_data`) — under investigation (§5b).

---

## 1. Branch / repo state

| Item | Value |
|---|---|
| Branch | `ble-qrcode-auth` (head of the runtime work) |
| Remote | `https://github.com/airy10/hass-localtuya.git` |
| Session commits (newest first) | `MODE_COLOR_ALIASES` fix (US/UK color spelling, next commit); `9696311` work_mode fallback; `061721a` JSON→DT_STRING; `f3e21a3` range enums + music alias; `189b0bb` color_mode fix; `bddd03d` Raw/Bitmap hex; `f2c1c8c` enum int→string; `c4a46ae`; `3c651ab`; `0d072bf` |
| Working tree | Clean after last commit |

The older `BLE_TRANSPORT_REVIEW_FIX_PLAN.md` and `STATUS.md` describe the *other* branch
(`fix/ble-transport-review`, never pushed) and are **not** the current work.

---

## 2. The user's device (ground truth)

- Name: `LGB102 蓝牙BK幻彩灯带 30点` (Bluetooth BK music light strip, 30 LEDs)
- MAC: `DC:23:4D:96:0A:40`; product `nvfrtxlq`; category `dd` (music strip)
- Credentials: id/password (IoT cloud mode), not QR
- **DP map** (from `Received datapoint update` lines in the 2026-08-13 log):
  - `1` = power (bool) — on/off works
  - `2` = `work_mode` (enum) — cloud values EXIST and use the **US spelling `"color"`**
    (confirmed: `_enum_string_for_id(2, 0)` returns `"color"` in the send log). Earlier
    "values empty" conclusion was WRONG — the real mismatch is US/UK spelling.
  - `3` = `bright_value` (int) — **never echoed by the device** (0 occurrences in the 16:13
    log) → dead dp in the current mode; brightness must ride `colour_data.v`
  - `5` = `colour_data` (string, 12-char HSV `h s v` each 4 hex: `h:0-360, s:0-1000, v:0-1000`)
    — echoed back on every write
  - `7`, `102`, `103`, `104`, `106`, `108` = read-only/state dps (echoed once at startup)
- Startup status seen: `dp1=True, dp2=0, dp5=010f02a803e8` (h=271°, s=680, v=1000)
- **mode 0 = colour** for this device (evidence in §4) — the strip was already in colour
  mode, but because our code couldn't map mode 0 it treated the light as non-color
  (`is_color_mode=False`), routing brightness to `bright_value` instead of `colour_data.v`.

## 3. Symptom → root cause chain (do not lose this)

Log evidence from `home-assistant_2026-08-13T15-56-50.410Z.log`:

```
Sending datapoint update, id: 5, type: DT_STRING: value: 005102c603e8   # color sent OK
...
Failed to set values {'5': '005102c603e8', '2': 'colour'} --> invalid literal for int() with base 10: 'colour'
```

1. `light.async_turn_on` builds `{color_dp: value, mode_dp: "colour"/"white"}`.
2. `BluetoothTransport.set_dps` → `_enum_index_for_id(2, "colour")` fails (cloud `values`
   empty) → returns the string unchanged → `set_value("colour")` → `int("colour")` → `ValueError`.
3. The color/brightness dp was already sent (dict order), the device ACKs it (result 0) and
   even echoes the new dp value back — **but ignores it** because the mode never changes.
4. Because the read side also failed to map mode `0` (empty values), `is_color_mode=False`,
   so brightness-only changes were sent to `bright_value` (dp 3) — which this device does
   not apply — instead of the `colour_data` v-channel.

Result: "color control seems wrong, brightness has no effect", while on/off works.

**Correction (16:13 log, post-`9696311`):** the writes no longer fail — the actual root cause
turned out to be a **US/UK spelling mismatch**: the cloud `work_mode` values use `"color"`
(US) while localtuya's constants use `"colour"` (UK). `_enum_string_for_id(2, 0)` → `"color"`
(log line `Sending datapoint update, id: 2, type: DT_ENUM: value: color`), and the light
compares against `"colour"` → `is_color_mode` always False. The `9696311` fallback still
helped: writes of `"colour"` now map to index 0 via `WORK_MODE_FALLBACK` (cloud has no
`"colour"`), so the mode write succeeds and the device echoes `0`.

## 4. Reference component findings (`/Users/airy/Sources/airy/github/ha_tuya_ble`)

This is the ground truth the fixes were derived from:

- `custom_components/tuya_ble/light.py:127-143` — `ProductsMapping["dd"]["nvfrtxlq"]` overrides
  `work_mode` values to `{colour, dynamic_mod, scene_mod, music}` with comment *"So we still
  get the right enum values if the product isn't set to DP mode in the cloud settings."*
  **No `white` in the list** → white is expressed via `colour_data` with saturation 0.
- `devices.py:116-135` `_send_command` — for string values: JSON/STRING → `DT_STRING`;
  ENUM → `int_value = 0` default; maps via `values["range"].index(value)` only if `values`
  is a dict with a list `range`. For nvfrtxlq the override is broken by a bug
  (`tuya_ble.py:375` `values = description.values_overrides.values` — missing `()`, assigns
  a bound method), so `isinstance(..., dict)` is False and **work_mode is always sent as 0**.
- `light.py:614-741` `turn_on` — order is **power → work_mode → colour_data**; brightness in
  HS mode is written into **`colour_data` v-channel** (line 641-700), NOT `bright_value`.
  The `v` remap uses cloud `v` max (1000). `colour_data` format
  `"{:04x}{:04x}{:04x}".format(h, s, v)` for 12-char HSV.
- `light.py:815-828` — `color_mode` = HS when work_mode != "white" (raw int ≠ "white" ⇒ HS).
- Conclusion: **mode 0 = colour** for this device; writing mode 0 + colour_data is what makes
  color/brightness work; there is no dedicated white mode.

## 5. Fixes (all committed + pushed on `ble-qrcode-auth`)

| Commit | Change |
|---|---|
| `f2c1c8c` | `TuyaBLEDataPoint.value` maps `DT_ENUM` int → cloud string (`_enum_string_for_id`); `BluetoothTransport.set_dps` reverse-maps string → int (`_enum_index_for_id`) |
| `bddd03d` | `DT_RAW`/`DT_BITMAP` read as hex string, write via `bytes.fromhex` (like Ethernet) |
| `189b0bb` | `light.color_mode` always returns a supported mode (fixes HA `unsupported color mode brightness` validation error) |
| `f3e21a3` | enum values in `{"range": [...]}` format + `MODE_MUSIC_ALIASES = ("dynamic_mod",)` |
| `061721a` | `_DPTYPE_TO_BLE[DPType.JSON] = DT_STRING` (reference sends cloud JSON as string) |
| `9696311` | `WORK_MODE_FALLBACK = ("colour", "dynamic_mod", "scene_mod", "music")` used when cloud `values` empty for a `work_mode`-coded dp; `"white"` maps to `0`. Added regression tests (`test_ble_work_mode_fallback_maps_enum_when_cloud_values_empty`, `test_ble_enum_mapping_uses_cloud_values_when_present`) |
| *next* | **`MODE_COLOR_ALIASES = ("color",)`** in `light.py` (`is_color_mode` accepts the US spelling) → `is_color_mode` True → brightness goes to `colour_data.v` instead of dead `bright_value`; plus a one-time debug dump of enum cloud values in `tuya_ble.update_description` (`_LOGGED_ENUM_VALUES`) to capture the real `work_mode` spec |

## 5b. Open issue: saturation stuck at max on the strip

In the 16:13 log the color writes carry correct, *varied* saturation
(`001b00c003e8` = h=27, s=192, v=1000; `015b005003e8` = h=347, s=80, v=1000; ...), the device
echoes dp 5, yet the user reports the strip always shows full saturation and full brightness.
Hue changes are assumed to work (user was "playing with colors"). Likely the device firmware
ignores the `s` channel (budget 30-LED strip) — not fixable from our side. The brightness
part IS fixable (v-channel routing, see §5) and should be verified first; if after that the
strip still ignores `s`, treat it as a device limitation. Also confirm with the user whether
"max saturation" is observed on the physical strip or in the HA color wheel.

Key code locations:
- `custom_components/localtuya/core/tuya_ble_lib/tuya_ble.py` — `WORK_MODE_FALLBACK`,
  `_enum_string_for_id`/`_enum_index_for_id`/`_is_work_mode` (~line 570+), `TuyaBLEDataPoint.value`.
- `custom_components/localtuya/core/transport/base.py` — `_DPTYPE_TO_BLE` (line ~31),
  `BluetoothTransport.set_dps` (line ~282).
- `custom_components/localtuya/light.py` — `MODE_MUSIC_ALIASES`, `color_mode` (line ~469),
  brightness/color encode paths (`async_turn_on`, `__to_color_v2`).

## 6. Tests

```bash
PYTHONPATH="<repo>:<repo>/custom_components:/Users/airy/Sources/Others/homeassistant-core" \
  /Users/airy/.venv/hass/bin/python -m pytest tests/ -q --no-header
```

→ **39 passed** (was 37; +2 for the work_mode fallback). `py_compile` clean on changed files.

## 7. Pending verification / next steps (where the next session must pick up)

1. **User must restart HA and test** (asked): pick a color → strip should change (hue works?);
   **brightness slider → should now work** (v-channel via `MODE_COLOR_ALIASES`); log should
   show `Sending datapoint update, id: 5, type: DT_STRING: value: ...` with the *v* field
   varying, and the new one-time line `enum dp 2 (work_mode) cloud values: {...}` — grab that
   dict, it reveals the full mode spec (music/scene/white strings).
2. **Effect-mode order guess**: `dynamic_mod`/`scene_mod`/`music` mapped to 1/2/3 is a best
   guess from the reference's listing. Mode **0 = colour** is solid (that's all color/brightness
   needs). If the user later reports music effects mapping to the wrong modes, swap the tuple
   order — the enum-values dump will settle it.
3. **Secondary**: music-mode control appears as the light's *effect* list, which only shows if
   the entity config has `CONF_MUSIC_MODE`/`CONF_SCENE` dp assigned (light.py:294-295, 438).
   No separate entity is expected. Not wired for the user's config yet — low priority.
4. If the fallback proves too aggressive for OTHER empty-value enum dps, scope it to product
   `nvfrtxlq` (device has `_device_info.product_id`); the reference scopes it per-product.
5. **Saturation**: after brightness is verified, ask the user whether hue changes and whether
   low-saturation picks (e.g. pastel) ever appear on the strip — if never, the strip ignores
   `s` and that's a device limit, not a code bug.

## 8. Useful log markers (user's HA debug log)

- `Sending datapoint update, id: X, type: Y: value: Z` → what actually went out
  (`core/tuya_ble_lib/tuya_ble.py:1478`)
- `Failed to set values {payload} --> {ex}` → a dp in the batch raised
  (`coordinator.py:562`, debug, force=True)
- `Received datapoint update, id: X, ...` → device-echoed status (16:13 log: only ids 2 and 5 echoed; 3 never)
- `enum dp X (code) cloud values: {...}` → one-time dump of the real enum spec (added with the color-alias fix)
- Full log examples: `/Users/airy/Downloads/home-assistant_2026-08-13T15-56-50.410Z.log` (pre-fix),
  `/Users/airy/Downloads/home-assistant_2026-08-13T16-13-28.114Z.log` (post-`9696311`)

## 9. Constraints / facts to respect

- User's HA pulls the GitHub branch directly → **commit + push** every fix.
- Ethernet must stay byte-for-byte compatible: `tuya_ble_lib` is imported only by BLE paths;
  shared `light.py` changes are behavior-identical for Ethernet string modes.
- Do not break `tuple` order semantics of `WORK_MODE_FALLBACK` without re-verifying against
  the reference.