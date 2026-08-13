# Architecture Alignment: LocalTuya-unified vs HA Core Tuya

> **Goal**: make our entity-type logic (light, switch, select, number, sensor, ...) as close as
> possible to the HA core `tuya` integration — only the *transport* differs
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

### Phase 3 — Entity logic parity

For each platform, move capability handling into the wrappers:

- **number**: use `IntegerTypeInformation` min/max/step/scale instead of manual
  `min_value/max_value/step_size` config only.
- **select**: derive `options` from `EnumWrapper.range` when `CONF_OPTIONS` empty (cloud
  fallback, exactly like core `DPCodeEnumWrapper.options`).
- **switch/binary_sensor**: gate availability on spec presence; adopt `skip_update` on
  echoes (`dp_timestamps`).
- **light**: already partially aligned (`color_data_spec`, `white_mode_supported`); move the
  remaining hardcoded mode tables (`MODES_SET`, `MODE_COLOR_ALIASES`, `WORK_MODE_FALLBACK`)
  to cloud-derived `work_mode` range — this removes the US/UK spelling patches entirely.
- **sensor/climate/fan/cover/humidifier/vacuum/...**: consume `TypeInformation` for units,
  scaling, and value validation.

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