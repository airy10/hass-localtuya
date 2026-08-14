# Definition-Driven Runtime Refactoring Spec

## Problem Statement

Core Tuya builds every entity from a **description** (`DeviceCategory` → `Tuya*EntityDescription` registry) resolved against the device's cloud spec (`function`/`status_range`/`status`, all keyed by **dpcode**). The entity `__init__` resolves wrappers by dpcode and the methods are thin `_read_wrapper` / `_async_send_wrapper_updates` calls.

LocalTuya already owns **most** of that machinery, but the *runtime* never uses it:

- We have the core-shaped category tables: `core/ha_entities/*.py` hold
  `LIGHTS: dict[DeviceCategory, tuple[LocalTuyaEntity, ...]]` (and `CLIMATES`,
  `FANS`, `SWITCHES`, …) declaring **DPCodes** exactly like core.
- We have cloud metadata: `core/cloud_api.py` (IoT platform) and
  `core/sharing_cloud.py` (Smart Life QR sharing SDK) provide `category`,
  `product_id`, `local_key`, and per-DP specs (`function`/`status_range`/
  `dps_data`) for every device in the account.
- We have the core-compatible spec surface: `coordinator.TuyaDevice` exposes
  `function` / `status_range` / `status` keyed by dpcode, plus `dp_wrapper_by_code`.
- The wrapper-decorator refactor (`SPEC_WRAPPER_REFACTORING.md`) already made
  every entity method a thin wrapper call.

What is **missing**: at setup time `gen_localtuya_entities()` /
`get_mapping_by_device()` / `derive_mappings_from_spec()` **flatten** the
category tables into `dps`-style config dicts (numeric `dp_id` strings) that
get persisted, and the runtime entity then re-resolves wrappers from that
flattened config by **dp_id** (`dp_wrapper_by_id`) instead of by dpcode from a
description. So the entity `__init__` and wrapper resolution still diverge
from core, and auto-config is a one-time flatten rather than a live definition
source.

**Goal** (two, in priority order):

1. **Max automation.** The user already added the device to their Tuya/Smart
   Life account. We use that account: authenticate → enumerate devices → build
   entities from `category` + specs, asking the user for **no** technical
   detail (no host/IP/local_key/dp ids).
2. **Core parity.** Entity classes (`light.py`, `switch.py`, …) become
   functionally identical to core: same wrapper attribute names, same
   description-driven `__init__`, thin methods — so a future core fix diffs
   cleanly onto our file.

## Current vs Target

```
                         CURRENT                              TARGET
  source of truth  →  persisted dps config (dp_id)     →  LocalTuyaEntity description (dpcode)
  wrapper resolve  →  dp_wrapper_by_id(config dp)      →  dp_wrapper_by_code(description dpcode)
  entity __init__  →  (device, dev_entry, dp_id)       →  (device, description)
  spec surface     →  function/status_range/status     →  same (already core-compatible)
  auto-config      →  gen_localtuya_entities() flatten →  description selection + live resolve
  manual config    →  the only runtime path            →  fallback "spec provider" only
```

## Core concepts

### 1. Entity description (exists) — `LocalTuyaEntity`

`core/ha_entities/base.py::LocalTuyaEntity` is already core-shaped:

```python
LocalTuyaEntity(
    id=DPCode.SWITCH_LED,            # "key" in core terms
    name=None,
    color_mode=DPCode.WORK_MODE,     # DPCodes, not dp ids
    brightness=(DPCode.BRIGHT_VALUE_V2, DPCode.BRIGHT_VALUE),
    custom_configs=localtuya_light(29, 1000, 2700, 6500, ...),
)
```

It carries `data` (friendly_name/icon/entity_category/device_class/state_class),
`localtuya_conf` (the DPCode-keyed config: `id`, `color_mode`, `brightness`, …),
`entity_configs` (localtuya-specific knobs like brightness range / kelvin range
/ music mode), and `contains_any` (DP-name gating). This is the object the
runtime should read — it is *already* the core `Tuya*EntityDescription`
equivalent.

### 2. Resolved definition (new) — per-platform `*Definition`

Core's `get_default_definition(device, switch_dpcode=..., ...)` returns a
`LightDefinition` holding the resolved wrappers (`switch_wrapper`,
`brightness_wrapper`, `color_data_wrapper`, `color_mode_wrapper`,
`color_temp_wrapper`). We add the same, e.g. `core/definitions.py`:

```python
@dataclass
class LightDefinition:
    switch_wrapper: DPCodeWrapper | None
    brightness_wrapper: DPCodeWrapper | None
    color_data_wrapper: DPCodeWrapper | None
    color_mode_wrapper: DPCodeWrapper | None
    color_temp_wrapper: DPCodeWrapper | None

def get_light_definition(device, description) -> LightDefinition | None:
    """Resolve wrappers for a light description; None if primary DP is absent."""
    if not (switch := _resolve(device, description.id)):
        return None                              # core's spec gate
    return LightDefinition(
        switch_wrapper=switch,
        brightness_wrapper=_resolve(device, description.brightness, BrightnessWrapper),
        color_data_wrapper=_resolve(device, description.color, StringColorWrapper),
        color_mode_wrapper=_resolve(device, description.color_mode),
        color_temp_wrapper=_resolve(device, description.color_temp, ColorTempWrapper),
    )
```

`_resolve()` = `dp_wrapper_by_code(device, dpcode)` for the primary DP (or the
first of a `(v2, v1)` tuple that exists in the spec), wrapped in the relevant
decorator from `core/dp_wrapper_decorators.py`. `dp_wrapper_by_code` already
returns `None` for unknown/unsupported DPs, giving the same "skip this
description" gating core applies.

### 3. Spec providers (new concept; surface exists)

The entity runtime must only ever see the core-compatible surface:
`device.category`, `device.function`, `device.status_range`, `device.status`.
Two providers populate it:

| Provider | Populates | Used when |
|---|---|---|
| **Cloud** | `category`/`product_id` from account; `function`/`status_range`/`status` from cloud specs (BLE passthrough / Ethernet `_cloud_dpspec_view`) | user logged in, device in account (default, automatic) |
| **Manual** | synthesized `function`/`status_range`/`status` from the persisted `dps` config; `dp_wrapper_by_code` misses → `RawDPWrapper` | LAN-only, unknown category, power-user override |

Concretely the manual provider synthesizes, per configured dp, a spec entry
keyed by `str(dp_id)` with `dp_id` set and no type, so `dp_wrapper_by_id` /
`RawDPWrapper` keep behaving exactly as today. This collapses the current
"manual is the only path" into "manual is a provider that feeds the *same*
runtime".

## Cloud usage invariant (BLE gap CLOSED)

Cloud is a **setup-time** dependency only: after a device is added, runtime
control must work with no cloud. Current state:

- **Ethernet — already correct.** `local_key` is persisted (`CONF_LOCAL_KEY`),
  and the full device cloud data (incl. `dps_data` = dp code/type/values/range)
  is persisted as `DEVICE_CLOUD_DATA` in the config entry.
  `coordinator._cloud_device_data()` prefers the live list but falls back to
  the persisted snapshot (merging persisted `dps_data` when live is missing).
  The only runtime cloud call is `_update_local_key`, fired solely on a
  key-error reconnect and gated by `CONF_NO_CLOUD`.
- **BLE — CLOSED (commit `e635599`).** `ble_manager._resolve_credentials` now
  reads the persisted `DEVICE_CLOUD_DATA` snapshot first (identity +
  `ble_specs` = functions/status_range) and only queries the cloud when the
  snapshot is incomplete or `force_update` is set. After a successful connect
  the coordinator persists the resolved credentials/specs back into
  `DEVICE_CLOUD_DATA` (writing only when they actually changed, so offline
  reconnects make no cloud call and no config-entry churn). BLE now matches
  Ethernet's setup-time-only cloud dependency.

**Status: DONE.** The invariant holds for both transports: the cloud is only
consulted at setup, or on an explicit forced refresh; otherwise the persisted
snapshot is authoritative.

## Design decisions (recommendations)

- **D1 — entity `__init__` signature.** Base becomes `__init__(self, device,
  description)` (description = `LocalTuyaEntity`). Platform `__init__` resolves
  wrappers from the description and stores them under **core's attribute
  names** (`_switch_wrapper`, `_color_data_wrapper`, `_color_mode_wrapper`,
  `_color_temp_wrapper`, `_brightness_wrapper`, …). This is the single biggest
  lever for "diff core fixes onto our file".
- **D2 — add `TuyaDevice.category` / `product_id` / `id`.** Today category is
  only reachable via `ble_device.category` or config-flow cloud data. Add
  core-compatible properties on the coordinator (BLE passthrough; Ethernet via
  `_cloud_device_data()`), so `get_*_definition` and the platform setup can
  resolve descriptions uniformly for both transports.
- **D3 — keep `_config` as a compatibility adapter during migration.** Existing
  platforms read `self._config.get(...)` / `self.has_config(...)` heavily.
  Introduce a thin adapter that maps the description (`data` +
  `localtuya_conf` + `entity_configs`) into the current `_config` dict shape,
  so each platform can migrate to reading the description in its own phase
  without a flag-day rewrite.
- **D4 — unique_id must NOT change.** Core uses `tuya.{device.id}{key}`; we
  keep `local_{device_id}_{dp_id}` (derived from the description's resolved
  primary dp_id). Changing it would orphan every existing entity; there is no
  migration value in aligning it.
- **D5 — auto-config persists the *selection*, resolves live.** Instead of
  persisting flattened `dps` config, persist which category/descriptions were
  selected; at runtime re-derive the definition from live cloud specs
  (falling back to the persisted cloud snapshot when offline). Manual `dps`
  config remains a first-class provider for users who opt out of cloud.
- **D6 — keep localtuya's extra light features** (scenes/effects/music,
  `is_color_mode`/`is_white_mode`/…). These are intentional supersets of core
  and stay; the wrapper-holding core-shaped fields sit alongside them.

## Gap analysis (per platform)

| Platform | Current wrapper resolution | Target |
|---|---|---|
| switch | `dp_wrapper_by_id` + `BitmapMaskWrapper` in `__init__` | `get_switch_definition` → `_switch_wrapper` |
| light | per-config-dp `dp_wrapper_by_id` + decorators | `get_light_definition` → core-named wrappers |
| fan | per-config-dp resolution | `get_fan_definition` |
| climate | per-config-dp `DictSelectorWrapper`/`ClimateTempWrapper` | `get_climate_definition` |
| cover | per-config-dp + `InvertedPercentageWrapper` | `get_cover_definition` |
| humidifier / water_heater / select / number / vacuum / alarm_control_panel | per-config-dp | `get_*_definition` |
| sensor / binary_sensor / siren / valve / lock / remote / button | per-config-dp (mostly raw) | `get_*_definition` (raw passthrough) |

The `ha_entities/*` tables already enumerate which DPCodes each category maps
to; the gap is purely "flatten to `dps` → resolve by id" versus "read
description → resolve by code".

## Phased implementation plan

### Phase 0 — coordinator + definition core
0. ~~Close the BLE cloud gap~~ **DONE (commit `e635599`)** — persist BLE
   credentials/specs and read the persisted snapshot first (cloud only to
   refresh); see "Cloud usage invariant" above.
1. **DONE** — `TuyaDevice.category` / `product_id` (core-compatible; BLE
   passthrough, Ethernet cloud data, fallback to the persisted snapshot).
   `id` already existed as an instance attribute.
2. **DONE** — `core/definitions.py` with `resolve()` (tuple fallback +
   optional decorator) + `get_light_definition` / `get_switch_definition`.
   The public resolver is named `resolve`, not `_resolve`; the remaining
   platforms (fan/climate/cover/...) are added in Phases 3-5.
3. **DONE** — `entity_config_from_description(device, description, platform)`
   in `entity.py` maps a category-table description (data + localtuya_conf +
   entity_configs) into the legacy `_config` dict (dpcode → dp_id via the
   device specs); `LocalTuyaEntity.__init__` gained an optional `config=` arg
   so the definition-driven path feeds the same `self._config` surface.
4. **DONE** — `tests/test_definitions.py` (15 tests): `resolve` gating/
   decorator, switch/light definition resolution, `category`/`product_id`
   fallback, and description → `_config` adapter (build/gate/CLOUD_VALUE).

### Phase 1 — switch.py (proof of concept)
- **DONE** — `LocalTuyaSwitch.__init__` accepts a `description` and resolves
  its wrapper by dpcode via `get_switch_definition` (bitmap mask still
  applied); the manual config-driven `dps` path is the fallback. The wrapper
  attribute keeps core switch's name `_dpcode_wrapper` (set from
  `definition.switch_wrapper`). `_process_device_update` gained a None-guard.
  `entity.descriptions_for_platform(device, domain)` was added as the
  category-table lookup helper.
- **DONE** — setup wiring: `async_setup_entry` now derives entities from the
  category tables via `_described_entity_specs` when a device has no manual
  entities for the platform. BLE keeps `_auto_entities_for_device` (per-product
  MAPPINGS take precedence); non-BLE (Ethernet/cloud) devices use the new
  description-driven path. Manual `dps` config stays the fallback.
- **DONE** — tests: `test_switch.py::test_switch_description_driven_resolution`
  (wrapper resolved by dpcode, no `dp_wrapper_by_id`),
  `test_switch.py::test_switch_auto_created_from_cloud_category` (setup wiring),
  and `test_definitions.py` descriptions lookup.

### Phase 2 — light.py (reference, most complex)
- **DONE** — `LocalTuyaLight.__init__` accepts a `description` and resolves the
  core wrappers by dpcode via `get_light_definition`: `_switch_wrapper`,
  `_brightness_wrapper`, `_color_data_wrapper`, `_color_temp_wrapper`. The
  manual config-driven `dps` path is kept as the fallback provider.
- **DONE (intentional delta)** — `_color_mode_wrapper` and `_scene_wrapper`
  stay raw config-driven reads (by dp_id) rather than coming from the
  definition. LocalTuya's mode classification (`is_white/is_color/is_scene/
  is_music_mode` + scene payloads) compares raw strings and has no core
  equivalent, so it needs the raw dp_id-keyed value; `get_light_definition`
  still resolves `color_mode_wrapper` for the definition surface, but the
  entity deliberately does not consume it. Documented under D6.
- Scene/effect/music features preserved (D6).
- **DONE** — test: `test_light.py::test_light_description_driven_resolution`
  asserts the four core wrappers are resolved by dpcode and decorated
  (DPCodeBooleanWrapper / BrightnessWrapper / ColorTempWrapper /
  StringColorWrapper).

### Phase 3 — climate, fan, cover (conversion-heavy platforms)
- **DONE** — `get_fan_definition` / `get_climate_definition` /
  `get_cover_definition` added to `core/definitions.py`; `fan.py` / `climate.py` /
  `cover.py` `__init__` accept a `description` and resolve core-named wrappers
  by dpcode via the definition (manual `dps` stays the fallback provider).

### Phase 4 — humidifier, water_heater, select, number, vacuum, alarm_control_panel
- **DONE** — `get_humidifier_definition` / `get_water_heater_definition` /
  `get_select_definition` / `get_number_definition` / `get_vacuum_definition` /
  `get_alarm_control_panel_definition` added; each platform `__init__` resolves
  its wrapper(s) by dpcode, removing the per-config-dp resolution on the
  description-driven path (manual `dps` remains the fallback).

### Phase 5 — sensor, binary_sensor, siren, valve, lock, remote, button
- **DONE** — `get_sensor_definition` / `get_binary_sensor_definition` /
  `get_siren_definition` / `get_valve_definition` / `get_lock_definition` /
  `get_remote_definition` / `get_button_definition` added (raw passthrough via
  the shared `DPCodeDefinition`); each platform resolves its primary DP wrapper
  by dpcode on the description-driven path. Lock/remote state machines keep
  reading secondary DPs from the config adapter (they have no core equivalent).

### Phase 6 — config flow (max automation)
- Cloud-first `async_step_auto_configure_device`: after
  `async_get_device_functions`, build entity **descriptions** (not flattened
  `dps`), persist the selection, and let runtime resolve live. Keep manual
  `dps` and "no cloud" as escape hatches.
- Verify the existing QR sharing flow (`sharing_cloud.py`) is the default
  auth path and that Ethernet (IoT platform) and BLE both flow through it.

### Phase 7 — porting discipline
- Add a per-file mapping (localtuya entity → core entity) + a `SYNC CHECKLIST`
  (like `dp_types.py` / `dp_wrappers.py` already have) listing intentional
  deltas (transport abstraction, manual fallback, extra light features, naming).

## Test strategy
1. **Definition resolver unit tests** (`tests/test_definitions.py`): tuple
   fallback, spec gate (primary DP absent → None), decorator application,
   manual-provider fallback.
2. **Platform delegation tests**: assert entity `__init__` stores core-named
   wrappers and methods are thin (no `dp_wrapper_by_id`, no conversion math).
3. **Spec-provider tests**: cloud provider (Ethernet `dps_data`, BLE
   passthrough, offline snapshot) and manual provider (synthesized specs).
4. **Config-flow tests**: cloud auto-config produces descriptions; offline and
   manual paths still work.
5. **Regression**: full suite (currently 164 tests) must stay green; add the
   new tests incrementally per phase.

## Success criteria
- No `dp_wrapper_by_id` / `RawDPWrapper` in entity `__init__` bodies (only in
  the definition resolver / manual provider).
- Entity `__init__` signatures are `(device, description)` and store wrappers
  under core's attribute names.
- A new device in the Smart Life account can be added end-to-end with **no
  technical input** (host/local_key/dp ids never asked).
- `device.category` / `function` / `status_range` / `status` are the only
  surfaces the entity runtime reads.
- A core `light.py`/`switch.py` fix can be ported by diffing method bodies and
  `__init__` wrapper assignment, with all intentional deltas documented in the
  SYNC CHECKLIST.
- Manual `dps` config keeps working unchanged (it becomes the manual provider).
- All tests pass; no existing `unique_id` changes.
