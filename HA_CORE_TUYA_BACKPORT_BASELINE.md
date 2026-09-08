# Home Assistant Core Tuya Backport Baseline

Last inspected: 2026-09-07

- Home Assistant core checkout: `$HOME/Sources/Others/homeassistant-core`
- Reference checkout was compared directly against LocalTuya's category tables,
  definitions, wrappers, transports, diagnostics, and config flow.
- Core's Tuya dependency is now `tuya-device-handlers==0.0.27` in the inspected
  checkout (LocalTuya does not add it as a runtime dependency because the
  relevant type-information/wrapper layer is vendored in `core/`).
- LocalTuya baseline: the current working tree after the existing wrapper,
  definition-driven runtime, persistence, discovery, and quirk work.

## Applicable 2026-09-07 backport

The current Core tables add the `ZNJDQ` circuit-breaker category. LocalTuya now
covers the matching switch, relay-status/light-mode selects, and current,
power, voltage, and total-energy sensors. The required `DPCode` values were
already present locally, so this was a table-only backport with a regression
test in `tests/test_core_backports.py`.

The newer two-channel `CZ`/`KG` energy-meter work is already represented in
LocalTuya and was not duplicated. Core-only cloud features such as camera
stream allocation and feeder-scene services remain intentionally out of scope
for the local BLE/Ethernet transport.

Future comparisons should update this file with the inspection date, Core
revision/dependency versions, applicable table changes, and any intentional
non-backports.