# BLE Transport Review Fix Plan

Status: approved for implementation on `fix/ble-transport-review`; this document records the design baseline and validation contract.
Branch: `fix/ble-transport-review`
Base: `master`
Reviewed branch: `ble-qrcode-auth`

## 1. Purpose and scope

The `ble-qrcode-auth` branch adds BLE support, QR-based Smart Life authentication,
cloud-driven entity metadata, and a transport abstraction to LocalTuya. The review
against `master`, using `tuya_transport_merge_architecture.md` as the design
reference, found several issues in the BLE lifecycle and in the sharing-cloud
configuration path.

This plan defines the fixes before implementation. The goals are:

- make unsolicited BLE datapoint updates behave like Ethernet status updates;
- propagate BLE disconnects into the coordinator and entity availability lifecycle;
- make the transport contract internally consistent, including keep-alive;
- ensure Ethernet and BLE are both represented by the transport seam;
- preserve Ethernet behavior and existing configuration compatibility;
- make sharing-cloud automatic configuration use the same DP metadata contract as
  the legacy cloud path;
- make BLE metadata parsing work for read-only devices;
- make failed/cancelled BLE operations clean up their response state; and
- add deterministic tests before relying on physical hardware validation.

The plan has been reviewed and implementation is proceeding in the sequence below; the document remains the source of truth for scope and validation.

## 2. Current branch and repository constraints

- The repository's mainline ref is `master`; there is no `main` ref.
- The fix work is intentionally isolated on `fix/ble-transport-review`.
- The pre-existing, unrelated working-tree change to `README.md` must remain
  untouched and must not be committed as part of this work.
- BLE has only been import/compile verified so far. There is no physical Tuya BLE
  device available in the current environment, so hardware behavior must be
  explicitly marked as unverified until a device test is performed.
- The installed Home Assistant test environment currently has a `ConfigEntry`
  constructor mismatch (`subentries_data`), so full-suite failures must be
  distinguished from actual regression failures.

## 3. Architecture invariants to preserve

The parent architecture document establishes these invariants:

1. The coordinator should depend on a semantic transport contract rather than
   knowing protocol framing details.
2. Ethernet and BLE must expose equivalent operations:
   `status`, `set_dps`, `update_dps`, `keep_alive`, `close`, and connection state.
3. Runtime DP keys must be numeric `dp_id` values for both transports.
4. Unsolicited status updates must reach the common entity/coordinator path.
5. The Ethernet default path must remain backward compatible.
6. BLE credentials and DP metadata may come from the existing cloud abstraction;
   a second, divergent cloud stack should not be introduced.

The implementation should not solve a BLE problem by adding BLE-specific logic to
individual entity platforms unless the common transport/coordinator seam cannot
represent the behavior.

## 4. Findings and planned fixes

### 4.1 BLE unsolicited datapoints are not forwarded to LocalTuya entities

**Observed behavior**

`TuyaBLEDevice` invokes registered datapoint callbacks for notifications. The
`BluetoothTransport` callback currently updates only `dispatched_dps`. The
coordinator registers the Fingerbot event callback, but no callback calls
`TuyaDevice.status_updated()` for ordinary BLE datapoints.

Relevant locations:

- `custom_components/localtuya/core/tuya_ble_lib/tuya_ble.py`
  - `_fire_callbacks()`
  - `register_callback()`
- `custom_components/localtuya/core/transport/base.py`
  - `BluetoothTransport.__init__()`
  - `_handle_datapoints()`
- `custom_components/localtuya/coordinator.py`
  - `_make_ble_connection()`
  - `status_updated()`

**User-visible impact**

A BLE switch, alarm, sensor, or other device that reports a physical change can
remain stale in Home Assistant until a polling refresh. With a zero/default scan
interval, the update may never be observed after initial setup.

**Planned design**

Add a transport-level status listener, keeping the transport independent of the
coordinator type:

- Define a callback/listener contract in `core/transport/base.py`, preferably a
  small callable protocol or a `TransportListener` interface.
- Let `BluetoothTransport` accept/register a listener and invoke it with a
  numeric `dict[int, Any]` containing the changed datapoints.
- Make the transport callback use the datapoints supplied by the BLE library,
  not a snapshot of every current datapoint. This keeps `dispatched_dps` useful
  for event detection and avoids confusing a full status snapshot with a delta.
- Register a coordinator callback during `_make_ble_connection()` that calls
  `TuyaDevice.status_updated(status)`.
- Ensure callbacks are unregistered in `abort_connect()`/`close()` and are not
  duplicated when the same BLE transport is reused during reconnect.
- Preserve the existing Fingerbot callback as a separate behavior; its event
  filtering must continue to use the original datapoint objects and
  `changed_by_device`.

**Alternative considered**

Have `BluetoothTransport` call a global dispatcher directly. Rejected because it
would make the adapter Home Assistant-specific and violate the transport seam.
The listener should be injected by the coordinator.

### 4.2 BLE disconnects do not reach coordinator availability handling

**Observed behavior**

The vendored BLE library has `register_disconnected_callback()` and fires it from
its Bleak disconnect handler. No coordinator or transport callback is registered.
The BLE library may reconnect internally, but the common `TuyaDevice.disconnected()`
path is not called.

Relevant locations:

- `core/tuya_ble_lib/tuya_ble.py`
  - `register_disconnected_callback()`
  - `_disconnected()`
- `core/transport/base.py`
  - `BluetoothTransport`
- `coordinator.py`
  - `disconnected()`
  - `abort_connect()`
- `entity.py`
  - `LocalTuyaEntity.available`

**User-visible impact**

Entities can remain available based on their last non-empty status while the BLE
link is down. The coordinator also cannot cancel refresh handles, notify the
entity dispatcher, or coordinate reconnect state consistently.

**Planned design**

- Add an optional disconnect listener to `BluetoothTransport`.
- Register the coordinator's disconnect callback when creating the transport.
- Make the callback safe for both expected shutdown and unexpected disconnect:
  expected close must not schedule a reconnect, while unexpected disconnect must
  invoke the normal coordinator path exactly once.
- Track and unregister both status and disconnect callbacks with the transport.
- Make `BluetoothTransport.close()` idempotent and ensure it suppresses callbacks
  caused by its own expected shutdown.
- Avoid clearing the transport reference before the coordinator has had a chance
  to perform its normal cleanup; use the existing `TuyaDevice.disconnected()` /
  `abort_connect()` lifecycle consistently.
- Add tests for unexpected disconnect, explicit close, duplicate callbacks, and
  entity availability after disconnect.

### 4.3 `keep_alive()` is async but called without awaiting

**Observed behavior**

`Transport.keep_alive()` and both adapter implementations are declared async,
but `TuyaDevice._make_connection()` calls `self._interface.keep_alive(...)`
without awaiting it. The Ethernet adapter is currently unused; the BLE method is
a no-op but still produces an un-awaited coroutine.

Relevant locations:

- `core/transport/base.py`: `Transport.keep_alive()` and adapter methods
- `coordinator.py`: successful connection path
- `core/pytuya/__init__.py`: existing synchronous Ethernet keep-alive

**Planned design**

Use one consistent synchronous contract because the existing Ethernet protocol's
keep-alive starts/schedules work synchronously and BLE has no awaitable heartbeat:

- Change `Transport.keep_alive()` to a regular method returning `None`.
- Change `EthernetTransport.keep_alive()` to delegate synchronously.
- Change `BluetoothTransport.keep_alive()` to a synchronous no-op/logging method.
- Keep `close`, status, updates, and writes async where they perform I/O.
- Add a focused test that calling keep-alive creates no coroutine and delegates to
  the Ethernet protocol exactly once.

This is preferable to adding `await` in the coordinator because it preserves the
existing Ethernet protocol contract and prevents accidental scheduling changes.

### 4.4 Ethernet is not using `EthernetTransport`

**Observed behavior**

The coordinator still calls `pytuya.connect()` directly and stores the raw
`TuyaProtocol` for Ethernet. `create_transport("ethernet", protocol=...)` exists
but is not used.

**Planned design**

- Keep `pytuya.connect()` as the low-level connection factory.
- Immediately wrap its result using `create_transport("ethernet", protocol=...)`.
- Type `TuyaDevice._interface` as `Transport | None`.
- Route the existing Ethernet methods through `EthernetTransport` without
  changing their arguments or return values.
- Ensure the transport adapter exposes every method the coordinator currently
  uses: `add_dps_to_request`, `set_updatedps_list`, `reset`, `status`,
  `detect_available_dps`, `set_dps`, `update_dps`, `keep_alive`, `close`,
  `enable_debug`, `is_connected`, and `dispatched_dps`.
- Keep gateway/subdevice sharing behavior intact: subdevices must continue to
  reuse the gateway's already-wrapped transport.
- Add an adapter test using a fake protocol and retain existing Ethernet tests to
  prove behavior did not change.

This completes the architecture seam rather than adding a second special-case
interface for BLE.

### 4.5 Sharing-cloud individual auto-configuration lacks `dps_data`

**Observed behavior**

The individual device flow passes a sharing device record to
`gen_localtuya_entities()`. The sharing device record contains identity and
credential fields but does not contain the `dps_data` used for cloud-derived
ranges, scaling, and enum values. `async_get_devices_dps_query()` populates that
field only in a separate mass/diagnostic path.

Relevant locations:

- `config_flow.py`: `async_step_auto_configure_device()`
- `core/sharing_cloud.py`: `_device_to_dict()`,
  `async_get_device_functions()`, `async_get_devices_dps_query()`
- `core/ha_entities/__init__.py`: `gen_localtuya_entities()` and `get_dp_values()`

**Planned design**

Make the metadata contract explicit and populate it before individual generation:

- Add a helper on the cloud abstraction, such as
  `async_ensure_device_functions(device_id)`, that fetches and stores
  `device_list[device_id]["dps_data"]` for both `TuyaCloudApi` and
  `SharingCloud`, or make the existing `async_get_device_functions()` update the
  record consistently.
- In `async_step_auto_configure_device()`, await the helper for the selected
  device before calling `gen_localtuya_entities()`.
- Do not rely on the background task started by the options menu; config-flow
  correctness must not depend on a race.
- Preserve the existing returned `dps_strings` behavior for manual configuration.
- Ensure sharing and legacy cloud implementations expose the same shape:
  `dict[str, {code, type, values, accessMode, ...}]`.
- Add tests proving individual sharing auto-config receives `dps_data`, uses
  cloud-provided range/scale metadata, and still works when the metadata request
  returns an empty result.

### 4.6 BLE status metadata parsing skips read-only devices

**Observed behavior**

`TuyaBLEDevice.append_functions()` processes `status_range` inside
`if function:`. If the device has no writable functions, its read-only status
metadata is never added.

**Planned design**

- Process `function` and `status_range` independently.
- Treat `None` as an empty list for both inputs.
- Preserve later overrides/defaults behavior.
- Add a unit test with an empty function list and a non-empty status range, then
  assert that status mapping and numeric DP lookup work.

### 4.7 BLE packet failures leak response state and swallow cancellation

**Observed behavior**

`_send_packet_while_connected()` inserts a response future before writing. If the
write fails, cleanup is skipped. Retry tasks are created using the same packet
sequence. The low-level write method uses a bare `except`, converting cancellation
into `BleakError`.

Relevant locations:

- `core/tuya_ble_lib/tuya_ble.py`: `_send_packet_while_connected()`
- `_send_packets_locked()`
- `_int_send_packets_locked()`

**Planned design**

- Put response-future registration and removal in a `try/finally` block.
- On send failure, cancel the future and remove it from
  `_input_expected_responses` before re-raising.
- Preserve `asyncio.CancelledError` by adding an explicit `except
  asyncio.CancelledError: raise` before handling transport exceptions.
- Replace broad low-level exception handling with the specific Bleak/write
  exceptions that should trigger reconnect behavior; retain a final broad handler
  only if the library requires conversion for unknown backend errors.
- Ensure disconnect/reconnect retry tasks do not produce unhandled task exceptions:
  attach a done callback or route retries through a supervised task method that
  logs failures and observes the exception.
- Decide whether retry ownership belongs to the current command or the reconnect
  loop. The safer initial behavior is to let the current command fail cleanly and
  let the reconnect loop retry the next operation, rather than launching duplicate
  fire-and-forget resends with stale response state.
- Add tests for write failure, cancellation, response timeout, and retry-task
  completion.

## 5. Implementation sequence

The fixes should be implemented in this order:

1. **Transport contract and adapters**
   - Introduce listener types and normalize `keep_alive` to synchronous.
   - Wrap Ethernet protocol connections in `EthernetTransport`.
   - Add fake-protocol adapter tests.
2. **BLE callback lifecycle**
   - Add status/disconnect listener plumbing.
   - Register listeners from the coordinator and clean them up idempotently.
   - Add callback and availability tests.
3. **BLE library correctness**
   - Fix independent metadata parsing.
   - Fix response-future cleanup and cancellation behavior.
   - Add isolated protocol tests with fake BLE client/device objects.
4. **Sharing-cloud metadata**
   - Normalize metadata population for legacy and sharing clouds.
   - Await metadata before individual auto-config.
   - Add sharing-flow tests.
5. **Validation and cleanup**
   - Run focused tests, compilation, full tests where the HA environment permits,
     and `git diff --check`.
   - Remove only whitespace introduced in files touched by this fix; do not alter
     unrelated translation or README content unless necessary.

## 6. Test plan

### Unit tests

Add focused tests for:

- `EthernetTransport` delegation and synchronous keep-alive.
- `BluetoothTransport` status listener receives numeric DP deltas.
- BLE disconnect listener is called for unexpected disconnect and not duplicated
  on close.
- Coordinator callback forwards BLE status to `TuyaDevice.status_updated()`.
- `append_functions([], status_range)` populates status metadata.
- Failed BLE writes remove response futures.
- BLE task cancellation propagates `CancelledError`.
- Sharing cloud device auto-config awaits and stores DP metadata.

### Existing tests

Run:

```bash
python3 -m compileall -q custom_components/localtuya
/Users/airy/.venv/hass/bin/python -m pytest -q tests/test_p2f1_auto_config.py
/Users/airy/.venv/hass/bin/python -m pytest -q
git diff --check
```

The full suite's current `ConfigEntry`/`subentries_data` incompatibility should be
recorded separately if it remains. It must not be “fixed” by changing unrelated
test infrastructure in this branch.

### Hardware validation

When hardware is available, validate at least:

1. BLE device initial setup and cloud credential resolution.
2. Device-originated switch/sensor update without polling; verify the entity
   changes state while the configured scan interval is zero.
3. Device-originated disconnect; verify the entity becomes unavailable after the
   normal shutdown delay and returns to available after reconnect.
4. Repeated disconnect/reconnect cycles; verify callback registration does not
   multiply updates or bus events.
5. Write failure/reconnect behavior while an operation is in flight; verify no
   duplicate command is sent after recovery.
6. Read-only BLE sensor with no writable function list; verify its status DP is
   decoded and exposed.
7. Boolean false, numeric zero, enum zero, raw, and string BLE datapoints; verify
   falsey values are not dropped.
8. Multiple simultaneous BLE notifications; verify every changed DP reaches the
   common coordinator path and `device_dp_triggered` contains only the delta.
9. Sharing-cloud QR-authenticated device auto-configuration; verify cloud range,
   scale, step, and enum metadata are applied.
10. Sharing token refresh and expired-session reauthentication; verify refreshed
    token data is persisted without appearing in diagnostics.
11. Ethernet device setup and updates after the adapter migration; compare status,
    writes, refresh, heartbeat, and close behavior with the pre-migration path.
12. Gateway plus subdevice setup, including existing Ethernet subdevices, and
    confirm subdevices still share the wrapped gateway transport.
13. HA shutdown/reload during BLE connect, write, response wait, and reconnect;
    verify cancellation completes without leaked tasks or response futures.

## 7. Backward-compatibility and risk controls

- Do not change config-entry keys or transport default (`ethernet`).
- Do not remove the existing raw protocol implementation; only wrap it.
- Keep numeric DP IDs at the coordinator/entity boundary.
- Make callback registration idempotent because setup can pre-initialize BLE before
  the later connection task runs.
- Do not make entity platforms depend directly on `TuyaBLEDevice`.
- Avoid fire-and-forget operations for state transitions unless task exceptions
  are explicitly supervised.
- Keep cloud token data out of diagnostics.
- Preserve the pre-existing `README.md` modification and avoid committing it.

## 8. Definition of done

The implementation phase is complete only when:

- Ethernet and BLE both use the `Transport` abstraction.
- BLE push updates invoke the normal coordinator/entity update path.
- BLE disconnects correctly affect availability and reconnect lifecycle.
- No keep-alive coroutine is left un-awaited.
- Read-only BLE devices expose their status metadata.
- BLE failed/cancelled operations clean up response state.
- Individual sharing-cloud auto-config has the same DP metadata contract as the
  legacy cloud path.
- Focused regression tests pass.
- Compilation passes.
- Full-suite limitations are documented with the exact environment failure if the
  HA test dependency remains incompatible.
- No unrelated files are modified, and no hardware-tested claim is made without
  actual hardware evidence.

## 9. Implementation status

The approved fixes are implemented on `fix/ble-transport-review`:

- Ethernet connections are wrapped by `EthernetTransport` and the keep-alive
  contract is synchronous for both adapters.
- BLE status, connected, and disconnected callbacks are forwarded through the
  transport seam; reconnect completion triggers a coordinator status refresh.
- BLE read-only metadata parsing is independent of writable function metadata.
- BLE response futures are cleaned up on success, timeout, write failure, and
  cancellation; detached packet resends were removed in favor of the reconnect
  loop.
- Sharing-cloud DP metadata is stored and awaited before individual automatic
  entity configuration.
- Focused regression coverage now includes adapter callbacks, reconnect refresh,
  numeric Ethernet status keys, read-only metadata, retry cleanup, and sharing
  metadata.

Validation completed so far:

- `python3 -m compileall -q custom_components/localtuya tests`: passed.
- Focused tests (`test_transport_fixes.py` and `test_p2f1_auto_config.py`):
  **16 passed**, one Home Assistant deprecation warning.
- Full-suite failures remain limited to the pre-existing Home Assistant test
  fixture mismatch requiring `ConfigEntry(..., subentries_data=...)`.
- Physical BLE and Ethernet hardware validation remains outstanding.
