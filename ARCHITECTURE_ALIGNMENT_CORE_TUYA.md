# Architecture Alignment: LocalTuya-unified vs HA Core Tuya

> **Goal**: make our entity-type logic (light, switch, select, number, sensor, ...) as close as
> possible to the HA core `tuya` integration — including the **entity class implementations**
> (`switch.py`, `light.py`, ...): thin classes delegating to a shared capability layer, with
> config-flow construction preserved as our differentiator. Only the *transport* differs
> (we talk to devices over BLE/Ethernet, core talks to the cloud over MQTT).
>
> This document inventories both architectures, identifies the gaps, and proposes the
> alignment plan. It is a reference document; implementation happens in follow-up work.

## 1. The core insight: capabilities come from the cloud, not the transport

Both components get their **DP capability metadata** from the same source: the Tuya cloud
(`/v1.1/devices/{id}/specifications`). The transport (MQTT push, BLE GATT, local Ethernet
packets) only carries *values*; it says nothing about what a DP *is*.

- HA core `tuya` pulls specs via `tuya_sharing.Manager.update_device_cache()` and stores them
  on `CustomerDevice.function` / `CustomerDevice.status_range` (maps of `code → {type, values}`).
- Our component already does the same on the BLE path: `TuyaBLEDevice.append_functions()`
  (`core/tuya_ble_lib/tuya_ble.py:384-410`) stores the cloud-fetched `function`/`status_range`
  on the device; on the Ethernet path the same spec lives in `TuyaCloudApi` `dps_data`
  (`core/cloud_api.py:354-407`, merged from specifications + shadow properties + things model).

**Therefore**: the entity logic can (and should) be written once, consuming the *spec*, and
be transport-agnostic. This is exactly what we started with `color_data_spec`
(`coordinator.py:156-191`) and `white_mode_supported` (`coordinator.py:194-218`).

---

## 2. Side-by-side architecture comparison

| Aspect | HA core `tuya` | Our `localtuya-unified` |
|---|---|---|
| Domain / type | `tuya` — cloud-push, `iot_class: cloud_push` | `localtuya` — `local_push` (BLE/Ethernet) |
| Setup entry point | `DeviceListener.initialize()` → `Manager.update_device_cache()` (blocking, executor) | `TuyaDevice.async_connect()` → BLE pairing / Ethernet socket per device |
| Device model | `CustomerDevice` (`tuya_sharing/device.py:47-99`): id, name, category, product_id, online, status, function, status_range, local_strategy, support_local | `TuyaBLEDevice` (`core/tuya_ble_lib/tuya_ble.py:281+`): id, address, category, product_id, product_name, function, status_range, datapoints |
| DP capability model | `tuya_device_handlers/type_information.py` — `TypeInformation` per type (Boolean/Enum/Integer/Json/Raw/String/Bitmap), wrappers `DPCodeXxxWrapper` with `find_dpcode`, `read_device_status`, `get_update_commands`, `skip_update` | `TuyaBLEDeviceFunction` (`tuya_ble.py:268-279`): code, dp_id, type, values (raw dict, JSON auto-parsed). **No wrapper layer, no `find_dpcode`, no `skip_update`** |
| Entity creation | **Static per-category description tables** + spec gate: `SWITCHES[device.category]` then `get_default_definition(device, key)` returns `None` if DP absent (e.g. `switch.py:938-943`) | **Config-flow driven**: user picks DP id + entity type manually; auto-config via `gen_localtuya_entities()` (`core/ha_entities/__init__.py:82`) + BLE `mappings.py` |
| Category vocabulary | `DeviceCategory` StrEnum (`const.py:80-580`, ~130 documented + undocumented) | **No `DeviceCategory` enum** — free-string categories in `ha_entities/*.py` tables |
| DP vocabulary | `DPCode` StrEnum (`const.py:583-994`) | `DPCode` StrEnum in `core/ha_entities/base.py:93-891` (overlapping but not identical) |
| Discovery signal | `TUYA_DISCOVERY_NEW` (`const.py:37`) — every platform subscribes; new device bind → entities without reload | Config-flow steps (`async_step_auto_configure_device` `config_flow.py:986`); BLE auto-entities only when device has **zero** configured entities (`entity.py:94-99`) |
| State delivery | MQTT push → `dispatcher_send(TUYA_HA_SIGNAL_UPDATE_ENTITY_{device.id})` → `_handle_state_update` → per-platform `_process_device_update` with `skip_update` echo suppression + `dp_timestamps` | `dispatcher_send(localtuya_{device.id})` → `_update_handler` (`entity.py:236-256`) → `status_updated()`; **no skip_update / echo suppression** |
| Services | `services.py`: `get/set_feeder_meal_plan` (device-registry resolved) | `set_dp`, `update_dps`, `reload` (`__init__.py:58`, `services.yaml`) |
| Diagnostics | Entry + device, `customer_device_as_dict` (function/status_range/status/local_strategy/quirk), redaction | Entry + device, obfuscation, `cloud_devices` + `Discovered_Devices` (`diagnostics.py:33,64`) |
| Platforms | 18: alarm_control_panel, binary_sensor, button, camera, climate, cover, **event**, fan, humidifier, light, number, **scene**, select, sensor, siren, switch, vacuum, **valve** | 18: alarm_control_panel, binary_sensor, button, climate, cover, fan, humidifier, light, lock, number, remote, select, sensor, siren, switch, text, vacuum, water_heater. **No camera / event / scene / valve; has extra lock / remote / text / water_heater** |
| Entity base | `TuyaEntity` (`entity.py:15-109`): unique_id `tuya.{device.id}{desc.key}`, `available = device.online`, has_entity_name | `LocalTuyaEntity` (`entity.py:175+`): RestoreEntity + ContextualLogger, config-driven `_dp_id`, per-DP getter/setter/is_available |
| Entity classes | **Thin delegators** over `definition.X_wrapper` (e.g. `switch.py:954-997`: is_on/turn_on/_process_update all go through wrapper) | **Thick config-driven** classes touching raw DPs (`switch.py:50-151`: getter/setter/bitmap branching + `set_dp`) — target: wrapper-delegating bodies with config as construction source |
| Device registry link | `get_device_info()` (`util.py:66-92`): identifiers `(tuya, device.id)`, manufacturer/model/model_id | `device_info` (`entity.py:278-297`): identifiers `(localtuya, local_{id})`, model = config model |
| Quirks | `TUYA_QUIRKS_REGISTRY` keyed by product_id (`tuya_device_handlers/registry.py`) | **None** — hardcoded per-product tables in `mappings.py` (only 3 categories) |

---

## 3. What core has that we don't (capability / discovery gaps)

1. **TypeInformation + DeviceWrapper layer** — the biggest architectural gap. Core entities
   never parse raw DP values; they consume wrappers that know the type (Integer min/max/scale/
   step, Enum range, etc.) and can `find_dpcode` across `status_range`/`function`. We parse
   ad-hoc in each platform. **This is the layer to port.**
2. **`skip_update` / echo suppression with `dp_timestamps`** — core platforms decide whether a
   pushed update should be written to HA (avoids the entity briefly reflecting the value we
   just sent). We lack it.
3. **Category-driven entity discovery** — core creates entities from `device.category` +
   per-category description tables with a spec presence-gate. We create from user config, plus
   `ha_entities` auto-config (268 category entries across 18 tables — good coverage) and a
   **tiny** BLE `mappings.py` (3 categories: co2bj, wk, szjqr; 4 builder types).
4. **`TUYA_DISCOVERY_NEW` runtime entity addition** — core adds entities for newly bound
   devices without reload. Our BLE auto-entity path only fills empty entity lists at setup.
5. **`DeviceCategory` + unified `DPCode` enums** — core has both as the shared vocabulary.
   We have `DPCode` but no `DeviceCategory`; category strings are duplicated per table.
6. **Camera / event / scene / valve platforms** — core supports these (RTSP via
   `get_device_stream_allocate`, doorbell/button events, cloud scenes, irrigation valves).
   We have none. (Our extra lock/remote/text/water_heater have no core equivalent either.)
7. **Quirks registry** — core ships a product-id-keyed quirk system loaded from
   `config/tuya_quirks/`. We hardcode 3 products.
8. **`report_type` / `local_strategy` / `support_local`** — core uses these (from
   `/v1.0/m/life/devices/{id}/status` + `/dp-report-types`) to convert dpId→code on MQTT.
   For BLE we map dp_id↔code ourselves in `tuya_ble_lib`.

---

## 4. What we have that core lacks (worth keeping)

- **BLE transport** (no cloud round-trip needed at runtime) and **Ethernet local packets**
  (fully offline control).
- **Per-entity user override flexibility** — users can map any DP to any entity type manually;
  core is purely category-driven.
- **`color_data_spec` / `white_mode_supported`** — transport-agnostic capability derivation
  (the pattern to generalize).
- **Restore-on-reconnect** and per-DP getter/setter callbacks (`entity.py:206-217`).
- **Sharing-cloud (QR) auth** alongside legacy IoT-platform auth.

---

## 5. Alignment plan (phased)

### Phase 1 — Shared DP capability layer (the foundation)

Port the `tuya_device_handlers` model into our `core/` as a transport-agnostic layer:

- New `core/dp_types.py`: `TypeInformation` classes for `Boolean/Enum/Integer/Json/Raw/String/
  Bitmap` (mirror `tuya_device_handlers/type_information.py`), including Integer `min/max/
  scale/step` scaling and Enum `range`/`prepare_set_value` validation.
- New `core/dp_wrappers.py`: `DPCodeBooleanWrapper`/`EnumWrapper`/`IntegerWrapper`/... with
  `find_dpcode(device, code)`, `read_device_status(device)`, `get_update_commands(device,
  value)`, `skip_update(device, updated_props, dp_timestamps)`.
- `TuyaDevice` gains a generic `dp_type(code)` accessor that resolves the capability object
  from `ble_device.function/status_range` (BLE) or cloud `dps_data` (Ethernet) — generalizing
  what `color_data_spec`/`white_mode_supported` already do.
- **Test**: reuse `tests/test_transport_fixes.py` patterns; add spec-derivation tests per type.

### Phase 2 — Category + DP code vocabulary

- Add `DeviceCategory` StrEnum (`core/const.py`) mirroring core `const.py:80-580`.
- Align our `ha_entities/base.py` `DPCode` with core's `const.py:583-994` (reconcile
  differences; keep the extra BLE-specific codes like `COLOUR_DATA_RAW`, `SCENE_DATA_RAW`).
- Replace free-string category keys in `ha_entities/*.py` tables with `DeviceCategory` members.

### Phase 3 — Entity class & logic parity

**Yes — the plan targets class-type implementation parity** (`switch.py`, `light.py`, ...):
core's entity classes are *thin delegators* over a capability wrapper, ours are *thick,
config-driven* classes that touch raw DPs. The goal is class bodies whose read/write/update
flow delegates to wrappers exactly like core, while **keeping our config-driven construction
path** (manual DP mapping is our value-add — offline, BLE, arbitrary devices).

Core `switch.py` shape (thin, ~40 lines):
```python
class TuyaSwitchEntity(TuyaEntity, SwitchEntity):
    def __init__(self, device, device_manager, description, definition):
        super().__init__(device, device_manager, description)
        self._dpcode_wrapper = definition.switch_wrapper   # capability object

    def is_on(self) -> bool | None:
        return self._read_wrapper(self._dpcode_wrapper)

    async def async_turn_on(self, **kwargs):
        await self._async_send_wrapper_updates(self._dpcode_wrapper, True)

    async def _process_device_update(self, updated, dp_timestamps) -> bool:
        return not self._dpcode_wrapper.skip_update(self.device, updated, dp_timestamps)
```

Ours today (`switch.py:50-151`, thick, direct `set_dp`/`dp_value`, getter/setter/bitmap
branching, no wrapper). Target alignment, per platform:

- **Delegate reads/writes to wrappers**: `is_on` → `_read_wrapper(wrapper)`,
  `async_turn_on/off` → `_async_send_wrapper_updates(wrapper, value)`, adopt `skip_update`
  echo suppression. The wrapper resolves *by dp_id* (our config key) instead of core's
  dpcode — a `dp_wrapper_by_id(device, dp_id)` helper over `TuyaDevice.dp_type()`.
- **Constructor gains a resolved wrapper**: replace `getter`/`setter`/bitmap branching in the
  class body with one `self._dpcode_wrapper = dp_wrapper_by_id(device, self._dp_id)`; keep
  getter/setter/bitmap as *optional overrides* (they already exist for synthetic configs).
- **Descriptions & naming**: adopt `EntityDescription`-style `key`/`translation_key`/
  `device_class`/`entity_category` so auto-configured entities render like core; keep
  `_attr_translation_key = f"{platform}_{dp_id}"` as the config-driven default
  (`entity.py:192-195`).
- **Config stays the source of construction**; spec becomes the *default* source:
  - **number**: `IntegerTypeInformation` min/max/step/scale as defaults, user config as
    override (core `number.py:540-542` copies wrapper bounds into `_attr_native_*`).
  - **select**: `EnumWrapper.range` options when `CONF_OPTIONS` empty (exactly core
    `DPCodeEnumWrapper.options`).
  - **light**: already partially aligned (`color_data_spec`, `white_mode_supported`); move
    remaining hardcoded tables (`MODES_SET`, `MODE_COLOR_ALIASES`, `WORK_MODE_FALLBACK`) to
    cloud-derived `work_mode` range — removes the US/UK spelling patches entirely.
  - **sensor/climate/fan/cover/humidifier/vacuum/...**: consume `TypeInformation` for units,
    scaling, validation.
- **Keep what core lacks**: `extra_state_attributes` (current/voltage/consumption on
  switches), `RestoreEntity`/restore-on-reconnect, per-DP `getter`/`setter`/`is_available`
  callbacks — these are localtuva extras worth preserving.

### Phase 4 — Discovery & runtime entity addition

- Add `LOCALTUYA_DISCOVERY_NEW` signal + `async_add_device` path so newly paired/bound BLE
  devices create entities at runtime (mirror `coordinator.py:120-143`).
- Extend `mappings.py` to more categories and more builder types (cover/fan/light/number/
  select/button), or better: derive mappings from cloud spec + category tables instead of
  per-product hardcoding.

### Phase 5 — Capability platforms & polish (DONE — see §7.5)

- **event**: doorbell/button events (BLE Fingerbot already fires `localtuya_fingerbot_button_pressed`
  on the bus; wrap it as an `event` entity).
- **scene**: cloud scenes via `SharingCloud`/`TuyaCloudApi` when available.
- **camera**: BLE cameras are not practical; skip unless an Ethernet/cloud RTSP path exists.
- **valve**: add platform + `ha_entities/valves.py` table (core `SFKZQ` reference).
- **diagnostics**: include `function`/`status_range`/`status` in device diagnostics (we
  already dump cloud devices; surface the parsed spec too).
- **quirks**: optional product-id keyed registry replacing hardcoded tables.

---

## 6. Concrete first steps (recommended order)

1. `core/dp_types.py` + `core/dp_wrappers.py` (Phase 1) — unblocks everything else; reusable
   by all platforms with zero behavior change initially.
2. `DeviceCategory` enum + `DPCode` reconciliation (Phase 2) — mechanical.
3. select cloud-options fallback + number spec-driven min/max + light work_mode cloud
   derivation (Phase 3) — the three most visible improvements.
4. Runtime discovery signal (Phase 4) for BLE re-pairing UX.

> Note on SDK versions: core `manifest.json` pins `tuya-device-handlers==0.0.26` and
> `tuya-device-sharing-sdk==0.2.14`; the venv has 0.0.24 / 0.2.10. Our component pins
> `tuya-device-sharing-sdk~=0.2.4`. If we reuse `tuya_device_handlers` classes directly,
> align the pinned versions first.

---

## 7. Completed alignment work

### 7.1 Async update pipeline + echo suppression (all shared platforms)

- `_process_device_update` is now `async def(self, updated_status_properties: list[str],
  dp_timestamps: dict[str, int] | None) -> bool` in the base (`entity.py`) and in all six
  platform overrides (switch, sensor, select, number, siren, binary_sensor), matching core's
  signature exactly (no default for `dp_timestamps`; core `dp_timestamps` may be `None` and
  is passed through to `skip_update`).
- The `_update_handler` that drives it is async as well.
- Docstring is verbatim core: "Called when Tuya device sends an update with updated
  properties." / "Returns True if the Home Assistant state should be written, or False if
  the state write should be skipped."
- Ours keeps one guard core doesn't need: `if self._dpcode_wrapper is None: return True`
  (in core the wrapper always exists; ours may be `None` when no wrapper could be resolved
  for the configured dp_id).

### 7.2 Method order + docstring parity (all shared platforms)

Per user directive — "similar functions should be in the same order (with same
docstrings/comments if the functions match) in both core and our components class files" —
every platform's shared methods now appear in core's relative order with core's exact
docstrings. Ours-only config-driven extras (`flow_schema`, `_setter`/`_getter`, bitmap
helpers, `extra_state_attributes`, scene math, `_process_device_update` guard, etc.) stay,
positioned sensibly around the core-shaped block.

Core orders adopted:

| Platform | Shared method order (core relative order) |
|---|---|
| switch | `is_on` → `_process_device_update` → `async_turn_on` → `async_turn_off` |
| sensor | `native_value` → `_process_device_update` |
| fan | writes first: `async_set_direction` → `async_set_percentage` → `async_turn_off` → `async_turn_on` → `async_oscillate`, then reads: `is_on` → `current_direction` → `oscillating` → `percentage` |
| light | `is_on` → `async_turn_on` → `async_turn_off` → `brightness` → `color_temp_kelvin` → `hs_color` → `color_mode` (duplicates removed) |
| select | `current_option` → `_process_device_update` → `async_select_option` |
| number | `native_value` → `_process_device_update` → `async_set_native_value` |
| button | `async_press` (already matched) |
| siren | `is_on` → `_process_device_update` → `async_turn_on` → `async_turn_off` |
| binary_sensor | `is_on` → `_process_device_update` |
| humidifier | `is_on` → `mode` → `target_humidity` → `current_humidity` → `async_turn_on` → `async_turn_off` → `async_set_humidity` → `async_set_mode` |
| climate | writes first: `async_set_hvac_mode` → `async_set_preset_mode` → `async_set_fan_mode` → `async_set_humidity` → `async_set_swing_mode` → `async_set_temperature`, then reads: `current_temperature` → `current_humidity` → `target_temperature` → `target_humidity` → `hvac_mode` → `preset_mode` → `fan_mode` → `swing_mode`, then `async_turn_on` → `async_turn_off` |
| alarm_control_panel | `alarm_state` → `changed_by` → `async_alarm_disarm` → `async_alarm_arm_home` → `async_alarm_arm_away` → `async_alarm_trigger` |
| cover | `current_cover_position` → `is_closed` → `async_open_cover` → `async_close_cover` → `async_set_cover_position` → `async_stop_cover` |
| vacuum | `fan_speed` → `activity` → `async_start` → `async_stop` → `async_pause` → `async_return_to_base` → `async_locate` → `async_set_fan_speed` → `async_send_command` |

Notable docstrings now verbatim core (examples): switch `is_on` "Return true if switch is
on."; sensor `native_value` "Return the value reported by the sensor."; fan `async_turn_on`
"Turn on the fan."; light `async_turn_on` "Turn on or control the light."; select
`current_option` "Return the selected entity option to represent the entity state."; number
`async_set_native_value` "Set new value."; button `async_press` "Press the button."; siren
`async_turn_on` "Turn the siren on."; binary_sensor `is_on` "Return true if sensor is on.";
vacuum `async_send_command` "Send raw command."; alarm "Send Disarm/Home/Arm/SOS command."

Deliberate deltas kept (documented deviations):
- siren `is_on` keeps its bool-guard (`isinstance(state, bool)` before `self._is_on`
  fallback) — needed because the raw DP may be a string for non-boolean wirings.
- binary_sensor `is_on` stays config-`CONF_STATE_ON`-driven (wrapper returns raw enum
  values; core compares against a `state_on` value).
- climate `async_turn_off` docstring says "Turn the device off..." — core has a typo
  ("Turn the device on") which we did not reproduce.
- cover has no tilt support (`current_cover_tilt_position`/`async_set_cover_tilt_position`
  absent — no tilt config in our flow).

Verification: full pytest suite green (79 passed) after the async conversion and after
every alignment batch; `compileall` clean. Test coverage of the wrapper delegation lives in
`tests/test_wrapper_delegation.py` (16 tests: skip-gate semantics, command batching,
synthetic-config fallbacks, percentage/humidity math).

### 7.3 Phase 2 — `DeviceCategory` + `DPCode` vocabulary (DONE)

- `DeviceCategory` (137 members, verbatim from core `const.py` — name/value/order verified
  by AST parity script; docstrings kept after each member) plus 4 localtuya extensions
  (`DGNZK`, `GCJ`, `HDMIPMTBQ`, `QT`) in `core/ha_entities/base.py` (placed there so the
  per-table `from .base import ...` line already covers it — no import churn).
- `DPCode` reconciled to 876 assignments / **874 unique values**: every core `DPCode`
  value now exists here (parity script proves zero core values missing); 479 ours-only
  values retained. Two intentional duplicate-value aliases remain: `COUNTDOWN_USB =
  'countdown'` (pre-existing ours) and `FILTER_LIFE = 'filter'` (core's own alias of
  `FILTER`; core also has `FILTER_DURATION = 'filter_life'`). StrEnum dedupes aliases so
  both names resolve to the same member.
- All 19 `ha_entities/*.py` tables converted from string category keys to
  `DeviceCategory.X` members (232 occurrences, including bracket-appends like
  `LIGHTS["hdmipmtbq"]`, `NUMBERS["hdmipmtbq"] = NUMBERS["dj"]`,
  `BINARY_SENSORS["gcj"] = FAULT_SENSOR`); annotations now `dict[DeviceCategory, ...]`.
  String lookups still work: StrEnum members hash-equal their values, so
  `tuya_data.get("bh")` on a `DeviceCategory.BH`-keyed dict resolves (smoke-tested;
  `DATA_PLATFORMS` platform lookups unaffected).
- Verification: parity script (DeviceCategory 137/137 exact; core DPCode values missing:
  none), `compileall` clean, pylint E-level clean on `base.py`, no new >120-char lines,
  full suite 79 passed.

### 7.4 Phase 4 — Runtime discovery + spec-derived mappings (DONE)

- `LOCALTUYA_DISCOVERY_NEW = "localtuya_discovery_new"` in `const.py` (mirrors core
  `TUYA_DISCOVERY_NEW`, const.py:37-38).
- `TuyaDevice.device_key` property (`coordinator.py`): `get_device_key(device_config)` +
  `_{node_id}` for sub-devices — exactly the key under which the device is stored in
  `hass.data[DOMAIN][entry_id].devices` (mirrors `__init__.py:388-400`).
- `_make_ble_connection` fires `async_dispatcher_send(hass, LOCALTUYA_DISCOVERY_NEW,
  [device_key])` once a BLE transport exists. During entry setup the signal is a no-op
  (no platform subscribed yet); the target case is runtime pairing/binding/reconnect —
  mirrors core `coordinator.py:120-143` (`async_add_device`).
- Shared `async_setup_entry` (`entity.py`) subscribes `_async_discover_device(device_keys)`
  via `config_entry.async_on_unload(async_dispatcher_connect(...))`. The handler looks up
  the device by key, skips devices without a BLE transport or with manually-configured
  entities for the platform, reuses `_auto_entities_for_device`, and registers the new
  `LocalTuyaEntity` instances — mirrors core `async_discover_device` (switch.py:933-951).
- `_auto_entities_for_device` now idempotent: it skips auto-generating configs whose
  `CONF_ID`/`CONF_PLATFORM` already exist in `dev_entry[CONF_ENTITIES]`, so repeated
  discovery signals can't duplicate entities.
- `mappings.py` grew `derive_mappings_from_spec(device)`: instead of per-product
  hardcoding, any device with a cloud spec (`function`/`status_range`: dpcode → dp_id)
  gets its entity mappings derived on the fly from the (now `DeviceCategory`-keyed)
  `ha_entities` tables. Per-product `MAPPINGS` still win when present; otherwise the
  derivation kicks in. Resolution rules mirror `gen_localtuya_entities` (Enum vs tuple
  DPCode alternatives, first-present-wins) and the spec gate mirrors core
  `get_default_definition` (switch.py:938-943) — entities whose primary DP is absent from
  the device spec are skipped. Import is lazy (function-scope) to break the
  `ha_entities → platform → entity → mappings` import cycle.
- Tests: 3 new cases in `tests/test_p2f1_auto_config.py` (category-table derivation,
  unknown-category empty, unknown-product fallback-to-derivation). Full suite now
  **92 passed**.

### 7.5 Phase 5 — Capability platforms, diagnostics & quirks (DONE)

- **event** (`event.py` + `core/ha_entities/events.py`): BLE Fingerbot devices already fire
  `localtuya_fingerbot_button_pressed` on the HA bus (coordinator `_handle_fingerbot_button`);
  the new `LocalTuyaEvent(LocalTuyaEntity, EventEntity)` platform wraps that bus event as an
  `event` entity — `_attr_device_class = EventDeviceClass.BUTTON`, `_attr_event_types =
  ["pressed"]`, subscribed in `async_added_to_hass`, mirroring core's event platform (which
  turns doorbell/button DP updates into `EventEntity` triggers). Registered as
  `"Event": Platform.EVENT` in `PLATFORMS` with an (intentionally empty) `EVENTS` table in
  `DATA_PLATFORMS` — event entities are per-DP-configurable, not derived from category
  tables, so the table stays empty.
- **valve** (`valve.py` + `core/ha_entities/valves.py`): `LocalTuyaValve(LocalTuyaEntity,
  ValveEntity)` with `_attr_supported_features = OPEN | CLOSE`, `is_closed = not is_open`,
  `async_open_valve`/`async_close_valve` via `_async_send_wrapper_updates`, and verbatim core
  `_process_device_update` docstring. `VALVES` table mirrors core for `DeviceCategory.SFKZQ`
  (SWITCH + SWITCH_1..SWITCH_8 → "Valve", "Valve 1".."Valve 8").
- **scene** (`scene.py`): cloud scenes exposed via `SharingCloud.async_get_scenes()` /
  `async_trigger_scene()` (executor-jobs wrapping tuya_sharing `Manager.query_scenes` /
  `trigger_scene`; the legacy `TuyaCloudApi` has no scene endpoint). `TuyaSceneEntity(Scene)`
  mirrors core: `unique_id = f"tys{scene.scene_id}"`, `entry_type = DeviceEntryType.SERVICE`,
  `available = scene.enabled`, `async_activate`. Not in `PLATFORMS` (that dict doubles as the
  config-flow entity-type selector); instead forwarded separately in `__init__.py` via
  `async_forward_entry_setups(entry, (Platform.SCENE,))` — mirrors core `const.py:61`.
- **diagnostics** (`diagnostics.py`): `async_get_device_diagnostics` now surfaces the parsed
  BLE spec and live status alongside `DEVICE_CLOUD_INFO` — `function`/`status_range`
  (dpcode → dp_id/type/values from `TuyaBLEDeviceFunction`) and `status` (dp_id →
  value/type/timestamp from `TuyaBLEDataPoints`). `bytes` values hex-encoded. Secrets and
  `ble_address` stay obfuscated. Added public `TuyaBLEDataPoints.values()` to avoid exposing
  the private `_datapoints` dict.
- **quirks** (`core/quirks.py`): product-id keyed `QuirksRegistry` mirroring core's
  `QuirksRegistry` (tuya_device_handlers/registry.py). First entry: the Fingerbot button
  datapoint table (was `FINGERBOT_SWITCH_DP` in `const.py`) — each known Fingerbot
  product_id registers a `DeviceQuirk(button_switch_dp=...)`, and coordinator
  `_handle_fingerbot_button` now resolves the DP through the registry. Replaces a hardcoded
  table with the registry pattern.
- Tests: `tests/test_event.py` (device-id matching + `_trigger_event`), `tests/test_quirks.py`
  (registry population, lookup, unknown/missing product), `tests/test_diagnostics.py` (BLE
  spec/status surfacing, no-BLE skip). Full suite **92 passed**, `compileall` clean.

### 7.6 Spec persistence — save the cloud spec, rehydrate it locally (COMPLETE)

**Goal.** Core tuya's `async_turn_on/off` etc. are one-liners (`_async_send_wrapper_updates`)
because core *always* has a `_dpcode_wrapper` — its cloud spec (`function`/`status_range`) is
always available. Ours carries fallback branches (`_setter`/`_getter`, `_bitmap_mask`, raw
`set_dp`) because `dp_wrapper_by_id(device, dp_id)` returns `None` whenever the spec is missing
(cloud not configured, not yet fetched, or offline). If we **persist the cloud spec at device
setup time** and **rehydrate it at init**, the wrapper resolves for every cloud-set-up device,
the branches collapse, and we get core parity for the common case while keeping the manual
paths for local-only devices.

**Architecture map (verified, 2026-08-14).**

- The entity's `device` is always the coordinator `TuyaDevice` (`entity.py:234-239`), regardless
  of transport. For BLE, `TuyaDevice.ble_device` (`coordinator.py:152-157`) exposes the
  `TuyaBLEDevice`, which carries `function`/`status_range` populated from cloud credentials
  (`ble_manager.py:154-159` → `tuya_ble.py:384`). For Ethernet there is no device object: the
  pytuya protocol is hidden inside `EthernetTransport` and the core-compatible surface is
  *synthesized* by `TuyaDevice.function/status_range` (`coordinator.py:224-245`) from
  `_cloud_dpspec_view()` (`coordinator.py:263-277`), which reads
  `cloud_data.device_list[id]["dps_data"]`.
- `dp_wrapper_by_id` (`core/dp_wrappers.py:346-369`) scans `device.status_range`/`device.function`
  and returns `None` when the spec is absent → that is exactly when our fallback branches run.
- The full cloud spec *is* fetched during config flow: `async_get_device_functions(dev_id)`
  (`config_flow.py:1001` auto-configure, `:1754` validate_input) returns dp_id →
  {code, type, values, range, accessMode, ...} and stores it in-memory at
  `cloud_data.device_list[dev_id]["dps_data"]` (`cloud_api.py:403-405`). But the config entry
  only ever receives the flattened `CONF_DPS_STRINGS` (`config_flow.py:1468-1485`) — type/range/
  values are thrown away. `DEVICE_CLOUD_DATA` is written to the entry only in the mass-configure
  path (`config_flow.py:1315`) and is never read back at runtime.
- No on-disk spec cache exists. The only `Store` usages are sharing-token
  (`sharing_cloud.py:100`) and remote codes (`remote.py:153`).
- Choke-point for rehydration: `__init__.py async_setup_entry` between `async_prepare_ble()`
  (`:411`) and `async_forward_entry_setups` (`:414`) — every `TuyaDevice` exists, BLE
  `TuyaBLEDevice`s are initialized, and no wrapper has been built yet. BLE can then receive
  saved specs via `TuyaBLEDevice.append_functions()` (`tuya_ble.py:388-414`); Ethernet via a
  fallback in `_cloud_dpspec_view()` that reads the persisted entry data.

**Design (3 parts).**

1. **Save** — persist the full per-device spec (the `dps_data` dict) into the config entry
   under `entry.data[CONF_DEVICES][dev_id][DEVICE_CLOUD_DATA]["dps_data"]` at every setup path
   where it is available: `async_step_auto_configure_device` (single-device, currently drops it),
   `validate_input` (manual add), and the mass-configure path (already stores it).
2. **Rehydrate** — at the `__init__.py` choke-point, for each device: if the live cloud spec is
   missing but persisted data exists, inject it. BLE: `ble.append_functions(functions,
   status_range)` (derived from `dps_data`). Ethernet: `_cloud_dpspec_view()` falls back to the
   persisted `DEVICE_CLOUD_DATA` before returning `{}`.
3. **Backfill** — for entries created *before* this feature (no persisted spec), at init: if
   cloud is configured and the device is in `device_list`, call `async_get_device_functions`
   once and persist the result (lazy migration).

**Payoff (implemented).** For every simple single-wrapper platform, `_dpcode_wrapper` is now
never `None`: the constructor resolves `dp_wrapper_by_id(device, dp_id) or RawDPWrapper(dp_id)`
(`RawDPWrapper` = raw dp_id-keyed read/write with no type conversion, for spec-less/local-only
DPs), and switch additionally wraps the wrapper in `BitmapMaskWrapper` when `bitmap_mask` is
configured (reads `any(v & m ...)`, writes `bytes(v | m)` / `bytes(v & ~m)`). The coordinator
`status` property merges the raw dp_id-keyed entries after the dpcode view so both wrapper kinds
read correctly. Entity bodies (`is_on`, `native_value`, `current_option`, `alarm_state`,
`is_closed`, `async_turn_on/off`, `_process_device_update`, ...) collapse to the core one-liners
for switch, siren, valve, select, number, button, sensor, binary_sensor, alarm_control_panel;
the only remaining config-driven branches are the user-facing scaling/offset/state_on/options
handling that has no core equivalent. `_setter`/`_getter` were removed (dead code).

**Multi-DP platforms (fan, light, climate, humidifier, cover, vacuum) — collapsed (2026-08-14).**
Each configured DP resolves `dp_wrapper_by_id(device, dp) or RawDPWrapper(dp)`, guarded
`if <dp configured> else None` (never `RawDPWrapper(None)`); the primary switch DP resolves
unconditionally. This makes every wrapper non-`None` whenever its DP is configured, so the
`if wrapper/else raw set_dp` branches collapse to unconditional
`_async_send_wrapper_updates`/`_read_wrapper` calls:

- **fan** — all four DPs collapsed (switch, speed, oscillate, direction); percentage↔speed
  scaling, direction fwd/rev mapping, and `speed_count`/ordered-list handling stay config-driven.
- **humidifier** — all four DPs collapsed (switch, target/current humidity, mode); mode keeps the
  `_available_modes` `DictSelector` conversion on read (writes `to_tuya`); `_current_mode` cache
  and its `status_updated` override removed (dead).
- **vacuum** — fan-speed DP collapsed; `fan_speed` falls back to the `_fan_speed` cache when the
  wrapper has no value. Action DPs (power/stop/pause/locate/mode) intentionally stay config-driven
  `set_dp` — core resolves these via cloud spec actions we do not replicate.
- **light** — switch DP collapsed (`is_on`/`async_turn_on`/`async_turn_off`); brightness/
  color-mode/color-temp DPs keep their optional wrapper-or-cache reads (write_only), and color
  writes stay batched `set_dps`. The color data DP is deliberately excluded (config-driven
  v1/v2/base64 string encoding that no vendored wrapper decodes).
- **climate** — switch DP collapsed (`async_turn_on/off`, `_is_on` reads the wrapper with a bool
  check then the config `_state_on` comparison); temps/presets/swing stay config-driven.
- **cover** — set-position DP collapsed (`async_set_cover_position` writes via wrapper); the read
  path stays config-driven (inversion, timed math, bool/str decoding).

Remaining `if self._x_wrapper:` guards are only where the wrapper is *optional* (DP not
configured): light brightness/color-temp, climate `_hvac_switch_dp` fallback. Config-driven
conversions with no core equivalent (percentage scaling, DictSelector maps, timed cover math,
inversion) are the genuine LocalTuya delta and are kept in the entities.

**Tests.** Save (entry data contains dps_data after flow), rehydrate (BLE `append_functions`
called / Ethernet spec view falls back), backfill (init fetches + persists when missing);
`tests/test_dp_wrappers_raw_bitmap.py` (16 unit tests for `RawDPWrapper`/`BitmapMaskWrapper`);
`tests/test_switch.py::test_switch_bitmap_mask` (bitmap write/read integration); wrapper
delegation tests in `tests/test_wrapper_delegation.py` cover all six multi-DP platforms with a
`dp_wrapper_by_id` patch (the `or RawDPWrapper` fallback only triggers when the patch returns
`None`). Full suite: **110 passed**.

### 7.7 Wrapper decorator refactor — conversion moved out of entities (DONE)

Full spec: `custom_components/localtuya/SPEC_WRAPPER_REFACTORING.md`
(commit `a7a7816`).

The conversions §7.6 left "kept in the entities" (percentage scaling,
DictSelector maps, timed cover math, position inversion, color encode/decode,
climate temp precision/unit) are now owned by 14 composable decorators in
`core/dp_wrapper_decorators.py` that wrap an inner wrapper and convert one
step before delegating through its public `read_device_status` /
`get_update_commands` interface. Platforms were refactored to thin
`_read_wrapper` / `_async_send_wrapper_updates` bodies:

- select → `DictSelectorWrapper` (removed `status_updated`/`_state_friendly`)
- fan → `FanSpeedPercentageWrapper` + `FanDirectionWrapper` (removed `status_updated`)
- humidifier / alarm_control_panel / water_heater → `DictSelectorWrapper` (+ `ClimateTempWrapper`)
- cover → `InvertedPercentageWrapper` on the set-position write (movement state machine kept)
- climate → `DictSelectorWrapper` + `ClimateTempWrapper` + `HumidityCoefficientWrapper`
- vacuum → `fan_speed` fully thin
- light → `StringColorWrapper` + `BrightnessWrapper` + `ColorTempWrapper` (removed `status_updated`/`_color_temp_reverse`)

Also moved `ColorTypeData`/`map_range` into the decorators module, and fixed
`TuyaDevice.status` to derive dpcode keys from `status_range`/`function`.
Remaining `status_updated` overrides are all genuine state machines
(cover movement, vacuum activity classification, sensor base64 sub-sensors,
siren/lock/remote). 20 new decorator unit tests; suite **130 passed**.

### 7.8 BLE offline persistence — no cloud needed after setup (DONE)

Commit `e635599`. §7.6 persisted the Ethernet spec; BLE still resolved its
credentials/specs from the live cloud at connect time. Now
`ble_manager._resolve_credentials` reads the persisted `DEVICE_CLOUD_DATA`
snapshot first (identity + `ble_specs` = functions/status_range) and only
hits the cloud when the snapshot is incomplete or `force_update` is set; the
coordinator writes the resolved credentials/specs back into
`DEVICE_CLOUD_DATA` after a successful connect (only when changed). BLE now
matches Ethernet's setup-time-only cloud dependency. 4 new tests; suite
**134 passed**.

---

## 8. Next work — definition-driven runtime

The entity *method bodies* now match core, but the *runtime* still resolves
wrappers from the persisted `dps` config by dp_id, whereas core resolves from
a `DeviceCategory → EntityDescription` table by dpcode. LocalTuya already has
the core-shaped category tables (`core/ha_entities/*.py`) and the
core-compatible `function`/`status_range`/`status` surface — the gap is that
`gen_localtuya_entities()`/`get_mapping_by_device()` flatten the tables to
`dps` config at setup instead of handing the description to the entity.

Full plan: `custom_components/localtuya/SPEC_DEFINITION_DRIVEN_RUNTIME.md`.
Goals: (1) max user automation (cloud account → auto entities, no technical
input), (2) entity classes core-identical (`__init__(device, description)`,
core-named wrappers) so core fixes diff cleanly. Phased 0–7; Phase 0 step 0
(BLE offline persistence) is already done.