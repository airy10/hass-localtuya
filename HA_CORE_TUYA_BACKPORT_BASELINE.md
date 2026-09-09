# Home Assistant Core Tuya Backport Baseline

Last inspected: 2026-09-09

- Home Assistant core checkout: `$HOME/Sources/Others/homeassistant-core`
- Inspected Core revision: `07c10090753baacb13907535a4280014113be351`
- Latest Tuya-specific commit in that checkout: `92d86b02c46`
- Reference checkout was compared directly against LocalTuya's category tables,
  definitions, wrappers, transports, diagnostics, and config flow.
- Core's Tuya dependency is now `tuya-device-handlers==0.0.29` in the inspected
  checkout (LocalTuya does not add it as a runtime dependency because the
  relevant type-information/wrapper layer is vendored in `core/`).
- Core also uses `tuya-device-sharing-sdk==0.2.15`; LocalTuya intentionally keeps
  its compatible `tuya-device-sharing-sdk~=0.2.4` requirement because it uses the
  sharing SDK through its own compatibility layer.
- LocalTuya baseline: the current working tree after the existing wrapper,
  definition-driven runtime, persistence, discovery, and quirk work.

## Applicable backports through 2026-09-09

### ZNJDQ circuit breaker — already backported

Core added the `ZNJDQ` circuit-breaker category in three commits on 2026-09-07:

- switch: `SWITCH_1` and `CHILD_LOCK`
- select: `RELAY_STATUS` and `LIGHT_MODE`
- sensors: `CUR_CURRENT`, `CUR_POWER`, `CUR_VOLTAGE`, and `ADD_ELE`

LocalTuya covers these descriptions. The required `DeviceCategory` and `DPCode`
values were already present locally, so this was a table-only backport with
regression coverage in `tests/test_core_backports.py`.

### Two-channel CZ/KG energy meters — already represented

Core's 2026-09-05 work added channel-specific current, power, voltage, energy,
status, warning-threshold, and combined-energy datapoints. LocalTuya already
had the corresponding `CZ`/`KG` tables and `ALL_ENERGY`, so no duplicate table
change was needed.

### HCDD chasing-tape light — already represented

Core added the undocumented `HCDD` category and a standard light description on
2026-08-20. LocalTuya already has `DeviceCategory.HCDD` and the matching light
configuration (`SWITCH_LED`, `WORK_MODE`, `BRIGHT_VALUE`, `TEMP_VALUE`, and
`COLOUR_DATA`).

### Doorbell payload classification — already represented

Core removed the `DOORBELL` event device class from `ALARM_MESSAGE` and
`DOORBELL_PIC`, because those datapoints carry message/picture payloads rather
than the doorbell-ring event itself. LocalTuya's event descriptions do not
classify those payloads as doorbell events.

### Indicator-light translation — already represented functionally

Core added the `on` translation for indicator-light mode. LocalTuya's select
mapping already accepts the `on` value; no separate translation-only change is
needed for its local configuration-driven entity model.

### QCCDZ EV charger — backported in this revision

Core added support for `DeviceCategory.QCCDZ`:

- number: `CHARGE_CUR_SET` (`charging_current`), with a 1–255 A range in the
  Core fixture
- select: `WORK_MODE` (`charger_work_mode`)
- sensors: `WORK_STATE` (`charger_status`), `FORWARD_ENERGY_TOTAL`
  (`total_energy`), `CHARGE_ENERGY_ONCE` (`session_energy`), `POWER_TOTAL`
  (`total_power`), and `TEMP_CURRENT` (`temperature`)

LocalTuya already had QCCDZ support and several charger-specific entities, but
was missing the standard `CHARGE_CUR_SET`, `FORWARD_ENERGY_TOTAL`, `POWER_TOTAL`,
and `TEMP_CURRENT` descriptions. These descriptions have now been added while
retaining the existing LocalTuya-specific entries. `DPCode.CHARGE_CUR_SET` was
added and regression coverage was expanded in `tests/test_core_backports.py`.

LocalTuya keeps its existing QCCDZ scaling and richer charger-specific table;
the standard Core entries are additive rather than replacements.

### Light color-temperature capability range — parity cleanup

Core commit `45d351fe7fa` changed lights to use the library's
`ColorTempWrapper.MIN_KELVIN`/`MAX_KELVIN` defaults and to expose the resolved
wrapper range on the entity. LocalTuya already resolved color-temperature
wrappers and supported configured per-device Kelvin ranges. The local wrapper
now exposes `min_kelvin` and `max_kelvin`, and `LocalTuyaLight` derives its
reported range from the resolved wrapper when available, preserving manual
configuration as the fallback for spec-less/local-only devices.

## Intentional non-backports

- Core-only cloud functionality such as camera stream allocation and feeder
  services does not map to LocalTuya's local BLE/Ethernet transport.
- Core's synchronous service-registration cleanup and centralized generic
  `reauth_successful` config-flow cleanup do not apply directly to LocalTuya's
  different service and Smart Life reauthentication architecture.
- The Core `tuya-device-handlers` version bumps are not copied into
  `manifest.json`; LocalTuya uses its vendored wrapper/type-information layer.

Future comparisons should update this file with the inspection date, Core
revision/dependency versions, applicable table changes, and any intentional
non-backports. Pay particular attention to new category tables, new DPCode
members, changes in the vendored wrapper package, and local-vs-cloud behavior
that must remain deliberately different.
