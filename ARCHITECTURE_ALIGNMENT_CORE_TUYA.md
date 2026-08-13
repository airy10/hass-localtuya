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

### Phase 5 — Capability platforms & polish

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