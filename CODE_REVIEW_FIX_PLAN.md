# Code Review & Fix Plan — Local Tuya (Ethernet + BLE)

> Review date: 2026-08-21
> Reviewed at commit: `0dd5d87` (version 2026.08.21)
> Scope: `__init__.py`, `coordinator.py`, `entity.py`, `discovery.py`,
> `core/pytuya/*`, `core/transport/base.py`, `core/ble_manager.py`,
> `manifest.json`. (`config_flow.py` at 1,801 lines and the 20+
> `core/ha_entities/*` modules were only spot-checked.)

**Overall**: mature, well-commented codebase with a sensible architecture — a
`TuyaDevice` coordinator wrapping a clean `Transport` abstraction over two
backends (pytuya TCP protocol / vendored BLE lib), spec-driven entity
resolution mirroring core's tuya integration. Main risks: **in-place mutation
of config entry data**, **entity→device misregistration**, several
**task/exception-lifecycle issues**, and some **protocol-layer security
shortcuts**.

Each finding below has a status checkbox that is updated as fixes land on the
fix branch.

---

## 🔴 High priority

### 1. Shallow-copy mutation of persisted entry data — `[x] FIXED`

Locations:
- `__init__.py:176-198` (`_device_discovered`)
- `coordinator.py:975-1002` (`_update_local_key`)
- `__init__.py:478-485` (`_async_connect_cloud`)

```python
new_data = entry.data.copy()                      # shallow
...
new_data[CONF_DEVICES][dev_id][CONF_HOST] = device_ip   # mutates entry.data *in place*
```

`new_data[CONF_DEVICES]` is the same dict object as
`entry.data[CONF_DEVICES]`. Stored entry data gets mutated before
`async_update_entry`, so HA can't diff old vs new data, update listeners may
not fire correctly, and concurrent readers see torn state.
`_persist_ble_specs` (`coordinator.py:1036-1042`) does it correctly (per-level
dict copies) — inconsistent with the other sites.

**Fix**: deep-copy each nested level touched (`devices = dict(...)`,
`dev_entry = dict(...)` pattern) in all three sites.

### 2. Entities added to the wrong device — `[x] FIXED`

Location: `entity.py:75-129` (generic platform setup).

`entities` accumulates across all devices in the loop, but after the loop:

```python
device.add_entities(entities)   # 'device' = last device iterated
async_add_entities(entities)
```

With multi-device entries, every platform's entities get attached to one
`TuyaDevice`. Misroutes `restore_state_when_connected()`
(`coordinator.py:598`) and new-entity dispatch signals.

**Fix**: track entities per device and call `add_entities` inside the
per-device loop; keep a single `async_add_entities` call per device batch.

### 3. `TuyaProtocol.close()` can raise `CancelledError` into callers — `[x] FIXED`

Location: `core/pytuya/__init__.py:704-713`.

`clean_up_session()` cancels `heartbeater`; then `await self.heartbeater`
re-raises `CancelledError` into whoever called `close()` — e.g.
`abort_connect()` → `TuyaDevice.close()`, potentially interrupting remaining
teardown of other tasks/unsubs.

**Fix**: `await asyncio.gather(self.heartbeater, return_exceptions=True)`
(same for `_sub_devs_query_task`).

### 4. Session-key HMAC mismatch ignored + fixed nonce — `[x] FIXED`

Locations: `core/pytuya/__init__.py:1097-1104`, `:512`.

- HMAC check on `SESS_KEY_NEG_RESP` logs a warning but proceeds anyway (no
  `return False`). Wrong-key or MITM'd negotiation should abort the session.
- `local_nonce = b"0123456789abcdef"` is a fixed nonce; session keys derive
  from a constant + remote nonce. Upstream tinytuya generates it randomly.

**Fix**: `return False` on HMAC mismatch; use `os.urandom(16)` for
`local_nonce` (generated per-negotiation, not per-instance constant).

---

## 🟠 Medium priority

### 5. Timestamp written to `uid` instead of `t` — `[x] FIXED`

Location: `core/pytuya/__init__.py:1297-1299`.

```python
if "t" in json_data:
    t = time.time()
    json_data["uid"] = int(t) if json_data["t"] == "int" else str(int(t))
```

Sets `uid` to the epoch timestamp and leaves `t` as `"int"`/`""`. Upstream
pytuya sets `json_data["t"] = ...`. Devices tolerate it today, but this
corrupts both fields.

**Fix**: write to `json_data["t"]` (keep upstream semantics).

### 6. `async_setup_entry` returns `None` for stale entries — `[x] FIXED`

Location: `__init__.py:339-345`. HA expects `True`/`False`; returning `None`
is logged as a setup error.

**Fix**: return `False`.

### 7. Silent command loss in `set_status` — `[x] FIXED`

Location: `coordinator.py:834-848`.

`except (TimeoutError, Exception)` ≡ `except Exception`; failure downgraded
to debug log. Pending status was already cleared, so no retry happens — user
commands vanish invisibly.

**Fix**: warn on failure; re-queue payload into `_pending_status` so the next
connect/set attempt retries it.

### 8. Sync dispatcher calls in async context — `[x] FIXED`

Location: `coordinator.py:1076-1078` (`_dispatch_status`), `:942`
(`_shutdown_entities`). Use `async_dispatcher_send`; make call sites async
where needed.

### 9. Dead / broken code cleanup — `[x] FIXED`

- `async_remove_orphan_entities`: unconditional `return` at line 547 + debug
  `return` at 554 — entire function dead incl. "ENTITIES ORPHAN" log.
- `__init__.py:172-173`: `if device := hass_data.devices.get(device_ip): ...`
  no-op statement (also keyed by IP while devices dict is keyed by host).
- `connect()` trailing `except:` → unreachable raise (`pytuya:1360-1361`);
  also `except (Exception, asyncio.CancelledError)` re-raising is noise.
- Bare `except:` in `_negotiate_session_key` (`pytuya:1058`) and in
  `_make_connection` (`coordinator:587`) — catch specific exceptions.
- `discovery.datagram_received`: `except (json.JSONDecodeError, Exception)`
  redundant tuple.

### 10. Migration path v1 fall-through risk — `[ ] OPEN`

Location: `__init__.py:228-334`. Version-1 entries fall through to the ≤3
branch which indexes `CONF_ENTITIES` structures v1 layouts may not have;
success log fires even when nothing migrated.

**Fix**: explicit `elif` chain keyed on version, each branch returns after
updating; guard final log.

### 11. Heartbeat restart race — `[ ] OPEN`

Location: `core/pytuya/__init__.py:628-675`. `clean_up_session()` cancels
`heartbeater` but the reference clears only when the loop body exits. If
`keep_alive()` runs in that window, `if self.heartbeater is None` skips
creating a replacement → connection without keep-alive until next reconnect.

**Fix**: clear `self.heartbeater` synchronously at cancel time (or have
`keep_alive_loop` never own the clearing race — set reference None before
awaiting gather in close paths).

### 12. Blocking sequential BLE prepare during setup — `[ ] OPEN`

Location: `__init__.py:411-412`. `dev.async_prepare_ble()` awaited serially
for all devices before forwarding platforms; each attempt can burn bleak
timeouts → linear startup delay with offline BLE devices.

**Fix**: `asyncio.gather` concurrently.

### 13. Misleading dead check in BLE MAC verification — `[ ] OPEN`

Location: `ble_manager.py:186-198`. Fetches factory-info MAC, compares… and
only logs. Comment claims fallback that doesn't happen. Implement the
documented behavior or remove the check.

---

## 🟡 Low priority

### 14. Nits bundle — `[ ] OPEN`

- `is_sleep` getter performs `setattr(self, "low_power", True)` side effect
  (`coordinator:401-409`) — move flag setting out of the property.
- `set_dp`/`set_dps` magic `await asyncio.sleep(0.001)` coalescing
  (`coordinator:854, 864`) — add explanatory comment/helper.
- `get_entity_config` raises bare `Exception` (`entity:233`).
- `manifest.json`: unpinned requirements (`bleak`, `bleak-retry-connector`,
  `pycryptodome`); `cryptography` imported but undeclared — add loose pins +
  declare dependency.
- Sub-device reaches into gateway internals: `gateway._interface`
  (`coordinator:496`) — add accessor.
- `error_json` builds JSON via `%` string formatting (`pytuya:541-544`) —
  use `json.dumps`.
- `is_write_only` detects BLE via `"0" in manual_dps` — self-admitted hack;
  candidate for dedicated config flag (deferred).

---

## ✅ Things done well (keep)

- Clean `Transport` abstraction isolating coordinator from pytuya vs BLE
  semantics; adapter callbacks exception-guarded (`base.py:208-234`).
- Buffer-growth protection; parse errors never escape `data_received`
  (`pytuya:354-383`) with rationale comments.
- Timeout handling in `wait_for` avoids cascading cancellation into unrelated
  commands (`pytuya:296-308`).
- Offline resilience: persisting BLE credentials/specs into
  `DEVICE_CLOUD_DATA` (proper deep copies there).
- Sub-device ONLINE/OFFLINE/ABSENT state machine with hysteresis.
- Real test suite under `tests/`.

## Suggested fix order

Phase A (correctness): #1, #2, #3
Phase B (protocol/security): #4, #5
Phase C (HA compliance/UX): #6, #7, #8
Phase D (hygiene): #9, #10, #11
Phase E (perf/cleanup): #12, #13, #14

## Commit process (mandatory for every fix)

Full pre-commit review cycle, in order:
1. **diff** — review the complete diff before staging
2. **black** — `.venv/bin/black --check <changed files>` must pass
3. **tests** — `.venv/bin/python -m pytest tests/ -q`, all must pass
   (baseline: 203 passed)
4. **plan doc** — flip the finding's checkbox to `[x] FIXED`
5. **commit** — individual commit per fix

Each fix lands as an individual commit on the fix branch; this document's
checkboxes are flipped to `[x] FIXED` in the same commit.

Test environment: venv at `$PWD/.venv` (→ `$HOME/.venv/hass`); full HA
core tree at `$HOME/Sources/Others/homeassistant-core`.
