# Merging BLE support into hass-localtuya
## Architecture proposal for a pluggable Transport layer

**Author:** Sisyphus (analysis agent)
**Date:** 2026-08-07
**Scope examined:**
- `Airy10/ha_tuya_ble` — `custom_components/tuya_ble` (~6 260 LOC)
- `xZetsubou/hass-localtuya` — `custom_components/localtuya` (~7 400 LOC)

---

## 0. Decided approach (from discussion)

The direction is confirmed: **fork `hass-localtuya`** and extend it to natively support BLE devices in addition to Ethernet. Specifically:

1. **Branch of localtuya** keeps its structure and entity/coordinator model as the base.
2. **Add a BLE transport**, with device discovery, data formatting, reading and writing that is **local-adapted from the `ha_tuya_ble` project** (vendored protocol library + adapted discovery).
3. **Unified entities** (`light`, `climate`, `switch`, …) that work for **both** BLE and Ethernet — the same entity class drives a device regardless of the physical link.
4. Cloud DP metadata (`code↔dp_id`) is shared via localtuya's existing `TuyaCloudApi` — both transports already draw from the same Tuya specs source (§2.3), so no new cloud layer.
5. **Guiding principle:** keep the diff from the original upstream (`xZetsubou`/`airy10` hass-localtuya) as **small as possible**, so the branch is easy to follow and easy to merge back upstream later. This is a **two-pass** strategy:
   - **First pass** = minimal changes to the original so it supports BLE transport, with high-level/device-type class changes kept as small as possible, and **no duplication of device-type classes** — one `Light`/`Climate`/`Switch`/… shared by both BLE and Ethernet.
   - **Second pass** = anything ha_tuya_ble does better (richer entities, auto-config, extra platforms like `text`) is deferred and used to **improve the original itself**.

The rest of this document details how to implement that. Sections 3–9 are the "how".

---

## 1. Executive summary

`hass-localtuya` is a structured, well-maintained integration. Its core protocol (`core/pytuya/`) is already transport-aware — the framing/crypto is fully decoupled from reading bytes *because the codec is a framing codec and the socket is wired via an `asyncio` protocol*. `ha_tuya_ble` has a complete, self-contained BLE protocol implementation with a clean separation between a **credential manager** (`AbstaractTuyaBLEDeviceManager`) and the **protocol** (`TuyaBLEDevice`).

The cleanest seam is **NOT** to bolt BLE into `pytuya.TuyaProtocol` (their framing, crypto, command set and discovery differ entirely). Instead the right seam is to introduce a **transport abstraction** at the point where `coordinator.TuyaDevice` currently talks to `pytuya`. Both stacks share the same *semantic* interface:

- get device status as `dict[int → DPValue]`
- set one / several DPs
- receive asynchronous (unsolicited) status updates
- connect / disconnect / reconnect
- expose "available / connected" for HA availability

BLE and WiFi differ only in the *mechanics* of satisfying those semantics (framing, encryption, discovery, keep-alive). Therefore:

> **Design a `TuyaApi` (transport) abstract interface, with one implementation per physical link: `EthernetTransport` (wraps the existing `TuyaProtocol`) and `BLETransport` (wraps `TuyaBLEDevice`). Refactor `coordinator.TuyaDevice` to depend on the interface, not on `pytuya` directly.**

The two protocol libraries themselves (`core/pytuya` and `tuya_ble/`) are kept as-is (vendor-in), only a thin adapter is added.

---

## 2. What each side already gives you

### 2.1 hass-localtuya (Ethernet)

The networking/cloud side already has the important property: **`pytuya.TuyaProtocol` is an `asyncio.Protocol`** and in fact is already structured as:

```
asyncio.Protocol  (+ ContextualLogger)
   connection_made(transport)         ← injects asyncio transport
   data_received(data)               ← framing decoder
   connection_lost(exc)
   transport_write(data)             ← write lock / rate limiting
   connect(): loop.create_connection(...)   ← factory, port 6668
```

Key classes in `core/pytuya/__init__.py`:
- `TuyaProtocol` — the wire protocol object (framing, crypto, seqno, DPs).
- `MessageDispatcher` — buffers/inspects frames; routes responses to seqno waiters; invokes `callback_status_update` for unsolicited `STATUS` messages.
- `TuyaListener` (ABC) — `status_updated`, `disconnected`, `subdevice_state_updated`. **This is the clean listener interface**.
- `connect(...)` factory returning a connected `TuyaProtocol`.

The HA side is `coordinator.TuyaDevice(TuyaListener, ContextualLogger)`:
- holds `self._interface: TuyaProtocol`
- `_make_connection()` calls `pytuya_connect(...)` then `self._interface.status()`
- `set_dp/set_dps` → `self._interface.set_dps(payload, cid=...)`
- reconnect loop (`_async_reconnect`), keepalive via `_interface.keep_alive(...)`
- subdevice/gateway model (fake gateway), cloud key refresh (`_update_local_key`)

Entity layer (`entity.py` + platform modules) talks only to `TuyaDevice` (status dict + `set_dp/set_dps`), except for a couple of places that peek at `device._interface` (the `update_dps` service in `__init__.py` and config_flow). **Good news: the entity layer is already transport-agnostic.** That is the ideal integration point.

### 2.2 `ha_tuya_ble` (BLE)

A well-factored standalone integration:
- `tuya_ble/tuya_ble.py` — `TuyaBLEDevice`: full BLE protocol (GATT service `0xa201`, write char `0x2b11`, notify `0x2b10`, MTU 20, multi-packet reassembly, AES-CBC, pairing/login/session keys, DP (de)serialization).
- `tuya_ble/manager.py` — `AbstractTuyaBLEDeviceManager` (ABC) + `TuyaBLEDeviceCredentials`. **`HASSTuyaBLEDeviceManager` (cloud.py) implements it** by fetching credentials (local_key, uuid, category, product, functions/status ranges) from the Tuya cloud.
- `devices.py` — `TuyaBLECoordinator`, `TuyaBLEEntity` (a `CoordinatorEntity`), product DB, `TuyaBLEDataPoint`.
- `base.py` — `IntegerTypeData`, `EnumTypeData` helpers.

Key approximate contract `TuyaBLEDevice` presents:
- `async start()`, `async stop()`
- `register_callback(list[TuyaBLEDataPoint])` — unsolicited updates
- `register_connected_callback` / `register_disconnected_callback`
- `a datapoints: TuyaBLEDataPoints` collection, `status: dict[str, Any]` (code-keyed)
- `_send_datapoints` / `set_value` on a datapoint to send

Differences from pytuya:
| dimension | hass-localtuya (WiFi) | ha_tuya_ble |
|---|---|---|
| link | TCP : 6666 | BLE GATT |
| framing | `0x55aa` header, seqno/cmd/len/retcode/crc | security_flag+IV+cipher, packet numbers |
| crypto | AES-ECB/CBC + MD5/HMAC per dp payload | AES-CBC with per-session keys |
| DP keying | numeric index (1..N) in JSON payload | numeric index (1..M) with typed values |
| discovery | UDP broadcast (ports 6666/6667) | BLE advertisement/manufacturer data + cloud credential lookup |
| keepalive | heartbeat cmd every 8.3s | none/bgBT keepalive |
| status push | dispatcher `status_callback` | `register_callback` |
| addressing | host IP + device id + local key | BLE address + cloud-provided local key/uuid |

**They both ultimately expose `dict[int → DPValue]` (or code-keyed) plus the ability to set DPs.** That is the abstraction we want.

> **IMPORTANT CORRECTION:** I initially (wrongly) concluded hass-localtuya is "cloud-optional" for DP functions. This is **incorrect**. hass-localtuya already talks to the Tuya cloud for DP codes/functions — see **§2.3**. Cloud is only optional in the sense that a *manually-added* device can function without it; but the code↔DP mapping infrastructure is already there and mirrors ha_tuya_ble exactly.

### 2.3 Both projects already share the cloud DP-code source

Both stacks fetch DP metadata from the **same** Tuya cloud specs API and both merge `functions`/`status`:

| project | method getting cloud specs | stored as | keyed by |
|---|---|---|---|
| hass-localtuya | `TuyaCloudApi.async_get_device_functions()` → `/v1.1/devices/{id}/specifications` + `/v2.0/cloud/thing/{id}/shadow/properties` + `.../model` (`core/cloud_api.py`) | `device_list[id]["dps_data"]` | `str(dp_id)` each carrying `code`, `type`, `values`, `accessMode` |
| ha_tuya_ble | `HASSTuyaBLEDeviceManager._fill_cache_item()` → `/v1.1/devices/{id}/specifications` (`cloud.py`) | `TuyaBLEDeviceCredentials.functions` / `.status_range` | list keyed by `code` containing `dp_id`, `type`, `values` |

**That means the `code ↔ dp_id` mapping is already available in both projects from the same source.** The difference is only presentational:
- hass-localtuya stores it keyed by `int dp_id` and uses `code` only for auto-entity-template matching (`gen_localtuya_entities()`),
- ha_tuya_ble stores it as `code`-keyed lists and addresses DPs by `code` at runtime.

**Architecture consequence:** We do **not** need to add a new cloud layer, and we do **not** need to reconcile a divergence. The `BluetoothTransport` can build its `code→dp_id` table from localtuya’s existing `dps_data` (via the same `async_get_device_functions`), or reuse ha_tuya_ble’s manager output. Config **already** carries `DEVICE_CLOUD_DATA` per device from the auto-configure flow, so the mapping needed by BLE is already present at runtime. This resolves most of "question #1" below (see §8).

---

## 3. Proposed architecture

### 3.1 New module layout (in `custom_components/localtuya`)

```
core/
  pytuya/                          # UNCHANGED (vendored) — ethernet framing
  pytuya_bluetooth/                # NEW: vendored from ha_tuya_ble (renamed to avoid collision)
  transport/                       # NEW: the abstraction seam
    __init__.py
    base.py        -> Transport(ABC), TransportListener(ABC), DPValue, DPType
    ethernet.py    -> EthernetTransport  (adapter over core/pytuya.TuyaProtocol)
    bluetooth.py   -> BluetoothTransport (adapter over TuyaBLEDevice)
    factory.py     -> get_transport(config, ...)
```

Keep protocol implementations untouched. `transport/` only adapts.

### 3.2 The control objects of the semantic interface

We keep the semantics identical to what `pytuya` exposes today, so entity code and `coordinator` barely change:

```python
class DPType(IntEnum): RAW=0; BOOL=1; VALUE=2; STRING=3; ENUM=4; BITMAP=5

@dataclass
class DPValue:
    dp: int
    value: Any
    type: TuyaBLEDataPointType  # or pytuya equival.

class TransportListener(ABC):
    def status_updated(self, status: dict[int, DPValue]): ...
    def disconnected(self, exc=""): ...
    def subdevice_state_updated(state): ...   # keep for BLE gateway-less parity (unused in BLE for now)

class Transport(ABC):   # the "transport"
    @property
    def is_connected(self) -> bool: ...
    async def connect(self) -> None
    async def exchange(self, command, dps=None, cid=None) -> dict   # request/response for WiFi
    async def set_dp(self, value, dp_index, cid=None)
    async def set_dps(self, dps: dict, cid=None)
    async def status(self, cid=None) -> dict[int, DPValue]
    async def update_dps(self, dps=None, cid=None)
    async def close(self)
    async def keep_alive(self, is_gateway=False)   # WiFi: heartbeat loop; BLE: no-op / BLE-specific
    def enable_debug(self, flag, name=None)
    # wiring:
    def set_listener(self, listener: TransportListener)
```

Notes:
- We mimic `pytuya`'s current method set *exactly* (`set_dps`, `update_dps`, `status(cid)`, `keep_alive`, `enable_debug`, `is_connected`), so `coordinator` and `__init__.py`/service `update_dps` compile unchanged once they call the transport instead of `_interface`.
- For BLE, commands without `cid` and where "query status" is replaced by "subscribe to push updates" — see §5.
- `Transport` implementations may keep a `.device` handle if an entity needs device info (BLE).

### 3.3 EthernetTransport (adapter)

Thin adapter; mostly a rename/re-export with a wrapper to satisfy the ABC and expose `dps` as `DPValue`:

```python
class EthernetTransport(Transport):
    def __init__(self, host, did, local_key, protocol_version, enable_debug):
        self._inner: pytuya.TuyaProtocol  # built via pytuya.connect(...)
    # set_/status/update_/keep_alive/close -> delegate to self._inner
```

The bridge is already trivial since `pytuya.TuyaProtocol` exposes `set_dps`, `status`, `update_dps`, `keep_alive`, `is_connected`, and fires `listener.status_updated` for push. We only wrap to a DP normalization and to route the listener.

### 3.4 BluetoothTransport (adapter)

The heavier adapter. `ha_tuya_ble` exposes a notification/callback model instead of request/response `status()`. The adapter:

1. Wraps a `ha_tuya_ble.TuyaBLEDevice` obtained from a `AbstractTuyaBLEDeviceManager` (reuse ha_tuya_ble's `HASSTuyaBLEDeviceManager`, or localtuya's own `TuyaCloudApi` — both hit the same specs endpoint).
2. `register_callback` → normalize `list[TuyaBLEDataPoint]` → `dict[int, DPValue]` → `listener.status_updated`.
3. Implement `status()` as a cached snapshot accumulated from notifications (plus an explicit `update()` send to trigger a refresh).
4. `set_dps` → map dp id → code via the cloud metadata and call `_send_datapoints`.
5. `keep_alive` → no-op; `TuyaBLEDevice` already reconnects internally.
6. `is_connected` → based on the wrapper's own connected state (BLE `_is_paired`).

### 3.5 Entity unification — one `Light`/`Climate`/… for both transports

The **decided goal is a single entity class per platform** that works over both BLE and Ethernet. This is feasible and I verified it against both codebases:

**Evidence that the entity layers are already aligned on `dp_id` (int) at runtime:**
- `ha_tuya_ble` entities (`TuyaBLESwitchMapping.dp_id`, `TuyaBLENumberMapping.dp_id`, etc.) carry **numeric `dp_id`** fields; the cloud `code` is only used during discovery/auto-config (`find_dpcode`/`find_dpid` resolve code→id). At runtime they address DPs by **int dp_id** — exactly like localtuya entities do.
- `hass-localtuya` entities address DPs by **int `dp_id`** (`self._dp_id`, `device.set_dp(value, dp_index)`).
- The platform feature logic (light color math, climate mode maps, scaling, etc.) is already nearly identical — ha_tuya_ble's `light.py` even comments *"Most of the code here is identical to the one from the Tuya cloud Light component"*.

So the DP key at runtime can be **`int`** for both transports, and the single difference remains the **data exchange** (which transport is used).

**What "unified entity" requires on top of the Transport ABC:**
1. A **unified `LocalTuyaEntity` base** (extend the existing one) that:
   - exposes `dp_value(dp_id)` / `set_dp(dp_id, value)` / `set_dps(dict)` — currently already transport-agnostic (reads `self._status`, calls `self._device.set_dp`),
   - gains the BLE-side helpers (`find_dpcode`/`find_dpid`, `IntegerTypeData`/`EnumTypeData` scaling) as **shared utility**, not BLE-only.
2. A **unified device-handle** in the coordinator: `TuyaDevice` already is the single seam; it just needs to accept either transport and expose the same methods (`status`, `set_dps`, `update_dps`, `connected`, `is_write_only`).
3. **Platform files merge**: take the richer/cloud-driven BLE platform files (they already handle `IntegerTypeData`/`EnumTypeData` resolution) and fold in localtuya's config-driven options (manual DP selection, restore-on-reconnect, passive entities, write-only/sleep devices). The result: one `light.py`, one `climate.py`, etc.
4. **Config schema**: entities remain configured by **numeric DP** (localtuya-style); BLE devices get their entity/DP set auto-filled from cloud specs at config time (using `gen_localtuya_entities` + `dps_data`), so the user sees the same entity-editing flow for both.

**Coverage gap to plan for:** localtuya supports platforms BLE doesn't (`alarm_control_panel`, `cover`, `fan`, `humidifier`, `remote`, `siren`, `vacuum`, `water_heater`) and BLE adds `text`. The unified set should be the **union** (18 platforms); the extra BLE ones are implemented in the branch as new platform files, and BLE-only semantics (e.g. `fingerbot` special handling) are folded into the shared entity base via optional product-info hooks.

---

## 4. Discovery & config flow

Two additions, symmetric with what each project already has:

- **Ethernet:** existing `discovery.py` (UDP broadcast). Keep as-is.
- **BLE:** add a BLE discovery pass:
  - depends on the HA `bluetooth` manifest entry → the integration must declare `bluetooth` as a dependency (`manifest.json`).
  - On the "add device" config step, offer a selector that scans using `bluetooth.async_scanner()`/`advertisement` for devices with `TuyaBLE` manufacturer data (`0x07D0`) or service `0x0000a201`.
  - On selection, fetch credentials via a `AbstractTuyaBLEDeviceManager` implementation (reuse ha_tuya_ble's `HASSTuyaBLEDeviceManager` pointing at localtuya's cloud config) → get `local_key`, `uuid`, category, product, functions, status ranges.
  - Merge into existing per-device config.

Config schema (`config_flow.py`) extension starting the device step can be extended:
```
CONF_TRANSPORT = "transport"          # "ethernet" | "bluetooth"
CONF_BLE_ADDRESS = "ble_address"
```
Default remains `"ethernet"` (backward compatible; no migration needed beyond adding `transport` default). When `bluetooth`, replace the `CONF_HOST`/`CONF_PROTOCOL_VERSION` fields by `CONF_BLE_ADDRESS`, drop `CONF_NODE_ID`/gateway concepts, and key the device cache on the BLE address.

---

## 5. Integration with the existing coordinator

The **core change is small**: `coordinator.TuyaDevice._make_connection` currently does:

```python
self._interface = await pytuya_connect(...)
```

becomes

```python
self._interface = await make_transport(transport_config)   # factory in transport/factory.py
```

Everything downstream (`status_updated`, `_dispatch_status`, `set_dp`, `set_dps`, entity `.status`, `_async_refresh(→update_dps)`, `update_dps` service) reads/writes via the interface and thus works for both.

Differences to reconcile in the coordinator per transport:

| coord logic | ethernet | bluetooth |
|---|---|---|
| connect trigger | connect in `_make_connection` | connect on first needed command; subscribe notifications after |
| status fetch | synchronous `status()` resp | cached + subscription push |
| keepalive | `keep_alive(is_gateway)` | none; BLE handles reconnection internally |
| sleep devices | `device_sleep_time` | not needed (BLE out-of-band) |
| subdevices / gateway | supported | not applicable — a nominal value; keep the code path but BLE entry has no subdevices |
| `_update_local_key` (cloud re-key) | updates host + local_key | updates local_key/uuid (via cloud manager) |

Entity `available` flag uses `device.connected` — after the seam both transports set that consistently (BLE: when paired & subscribed; WiFi: `is_connected`).

---

## 6. What gets reused vs. what changes

Reuse as-is:
- `core/pytuya` (entire ethernet protocol) — untouched.
- `ha_tuya_ble/tuya_ble/` library — vendored into `core/tuya_ble_lib/` (renamed to avoid module collision).
- `TuyaCloudApi` + `core/ha_entities` auto-configure — **already provides the cloud DP-code↔id mapping** (`dps_data`) that the BLE transport needs; extend `async_get_device_functions` output if the BLE adapter needs the BLE-shaped `functions`/`status_range` list.
- `AbstractTuyaBLEDeviceManager` + `HASSTuyaBLEDeviceManager` (ha_tuya_ble's cloud credential manager) — reusable as-is, or skipped in favor of localtuya's cloud.
- Entity **feature logic** (light color math, climate mode maps, scaling) — largely identical across both projects already (verified in `light.py`/`switch.py`); these become the shared platform modules.
- Coordinator reconnect/abort logic — mostly unchanged except the two rows in the table above.
- `diagnostics.py`.

New / changed:
- `transport/` (the interface + Ethernet + BLE adapters + factory).
- `coordinator.py`: swap `pytuya_connect` call for factory; normalize `status` dict to `DPValue`.
- **`entity.py`**: extend `LocalTuyaEntity` to be the **single shared entity base** (add BLE-side `find_dpcode`/`find_dpid`/`IntegerTypeData`/`EnumTypeData` helpers as shared utilities, keep `dp_value`/`set_dp`/restore-on-reconnect). 
- **Platform files** (`light.py`, `climate.py`, `switch.py`, …): **merged** — one file per platform for both transports; fold BLE's cloud-driven resolution + localtuya's manual-config options into each.
- `config_flow.py`: add `CONF_TRANSPORT` + BLE discovery + BLE fields; auto-fill BLE entity DPs from cloud specs.
- `discovery.py`: add BLE scanner path.
- `__init__.py`: ensure `update_dps` service uses transport interface; ensure not reaching `._interface` (it currently does `device._interface.update_dps` — change to transport method).
- `manifest.json`: add `"bluetooth": []` dependency; add `bleak` and `bleak-retry-connector` as optional deps (BLE path only, import lazily).

---

## 7. Phased rollout / migration

### Phase 0 — no behavior change
- Vendor `ha_tuya_ble/tuya_ble/` as `core/tuya_ble_lib/`.
- Add `transport/` ABC with empty ethernet adapter identical to today. **Nothing breaks.**

### Phase 1 — refactor coordinator onto transport
- Refactor `TuyaDevice` to talk to `transport` (ethernet adapter only). Entities unchanged. Verify full Wi-Fi test-suite green.

### Phase 2 — BLE adapter standalone test
- Implement `BluetoothTransport`; unit+manual test against a real Tuya BLE device inside ha_tuya_ble (device-level).

### Phase 3 — discovery + config
- BLE selection in config flow, credential lookup, address-keyed device provisioning.

### Phase 4 — coordinator bridging + live dual-device test
- Wire both transports; test subdevice/light/climate/number/switch flows on each.
- **Unify one platform file** (e.g. `switch.py`) and verify it drives both an Ethernet and a BLE device; then roll the pattern to the remaining platforms.

### Phase 5 — full entity unification
- Merge all platform files into the single shared set; fold BLE `fingerbot`/product hooks and localtuya's manual-config options into the shared base.
- Add the BLE-only platforms (`text`) and cover the localtuya-only ones on BLE where the hardware supports them.

### Phase 6 — diagnostics/service updates
- `diagnostics.py` for BLE (RSSI, MTU, connection attempt counts); keep `update_dps` service; expose `reconnect` via listener.

Phase 0–3 are independent and safe; Phases 4–5 are the entity-unification work; Phase 6 is polish.

---

## 8. Open questions / decisions

1. **DP identifier type** (CONFIRMED): the runtime key is **`int dp_id`** for both transports. Verified: ha_tuya_ble entities carry `dp_id: int` fields and only use cloud `code` during discovery (`find_dpcode`/`find_dpid`); localtuya entities already use `int dp_id`. The BLE adapter resolves `code→dp_id` from cloud metadata (§2.3) once at setup. Entities stay numeric-DP-configured for both. No divergence.

2. **Cloud requirement** (CONFIRMED): BLE requires cloud, reusing localtuya's existing `TuyaCloudApi`; manual no-cloud entry is advanced/optional only. `ha_tuya_ble` requires cloud to map BLE MAC → credentials/function specs; BLE devices aren't self-describing over GATT for entity mapping. hass-localtuya already has this exact cloud layer (`TuyaCloudApi.async_get_device_functions`), so:
   - (recommended) BLE transport reuses localtuya's existing cloud + `DEVICE_CLOUD_DATA`; no new cloud code needed.
   - (advanced, no-cloud) manual entry of BLE address + copy of specs/local_key for devices with a few numeric DPs.
   Recommend the first as first-class, the second as advanced. `CONF_NO_CLOUD` already exists (True at runtime by default, toggled in the flow), so BLE should simply require cloud enabled or the manual fallback.

3. **Availability semantics**: BLE is connection-oriented and can vanish from range — coordinator should mark unavailable faster; keep the BLE's existing reconnect/backoff (already built-in).

4. **Naming/namespace**: module names `tuya_ble` and `pytuya` differ; ensure `manifest.json` only pulls BLE deps when used — with a lazy import of the adapter.

5. **Style** (CONFIRMED): `DeviceConfig` dataclass (`const.py` `DeviceConfig`) currently hard-requires `CONF_HOST`. It must be extended to tolerate a `CONF_TRANSPORT=bluetooth` + address (no `host`) — a small coordinated change in `const.py`, `coordinator`, `config_flow`.

6. **Minimal-diff guiding principle** (CONFIRMED): keep the diff from the original upstream (xZetsubou/airy10 hass-localtuya) as small as possible, so the branch is easy to follow and easy to merge back upstream later. This is a **two-pass** strategy: **first pass** = minimal changes to the original so it supports BLE transport, with high-level/device-type class changes kept as small as possible and **no duplication of device-type classes** (one `Light`/`Climate`/`Switch`/… shared by both BLE and Ethernet); **second pass** = anything ha_tuya_ble does better (richer entities, auto-config, extra platforms like `text`) is deferred and improves the original itself. Implications:
   - Prefer **additive** new files over rewrites; don't restructure existing files wholesale.
   - Start from localtuya's existing platform files and **ADD BLE handling** rather than replacing them with ha_tuya_ble's files.
   - Vendor only the BLE protocol core as a new module `core/tuya_ble_lib/`; keep HA-facing code on localtuya's model.
   - Keep localtuya's manual numeric-DP config schema; BLE auto-fills from cloud.
   - **First-pass coverage** = localtuya's existing platforms only; BLE-only platforms (e.g. `text`) are deferred to the second pass.

7. **Q6 — BLE MAC ↔ cloud device linkage** (CONFIRMED, Option A): keep localtuya's UUID-based identity. Pass 1 = user manually links a discovered BLE MAC to a cloud device via a new `CONF_BLE_ADDRESS` field; **no new cloud API** (no factory-info). Pass 2 = adopt ha_tuya_ble's factory-info MAC map (`/v1.0/iot-03/devices/factory-infos`) to auto-fill the MAC. Rationale: zero new cloud code, zero new failure modes, minimal diff; manual MAC entry is the only friction.

8. **Q7 — Vendoring scope** (CONFIRMED): vendor only the BLE protocol core as `core/tuya_ble_lib/` (`const.py`, `manager.py`, `exceptions.py`, `tuya_ble.py`, `__init__.py`). Re-implement HA-facing parts on localtuya's model. Add `bleak`, `bleak-retry-connector`, `pycryptodome` to manifest requirements. Sever the `from ..const import (DPCode, DPType)` coupling (`tuya_ble.py:39`) by supplying `DPCode`/`DPType` from localtuya's const.

---

## 8.5 Pass-2 improvements (deferred from ha_tuya_ble)

Features ha_tuya_ble does better than localtuya, deliberately **not** implemented in pass 1 (minimal BLE support). Deferred to pass 2, which improves the original itself. Ranked by effort (S = small, M = medium, L = large). Full catalog: `.sisyphus/notepads/localtuya-unified/pass2_improvements.md`.

1. Factory-info MAC mapping (`/v1.0/iot-03/devices/factory-infos`) to auto-fill the BLE MAC (M).
2. Device-spec (functions/status_range) fetch + credential cache (M).
3. `IntegerTypeData`/`EnumTypeData` + `find_dpcode`/`find_dpid`/`remap_value` type helpers (M).
4. Per-product entity mapping tables + auto entity generation (L).
5. `text` platform (BLE fingerbot program editor) (M).
6. `translation_key` + `has_entity_name` (S).
7. Per-enum icons + `entity_registry_enabled_default` (S).
8. RSSI / diagnostic sensors (S).
9. Getter/setter + `is_available` mapping callbacks (M).
10. Bitmap-mask switches (S).
11. Typed datapoints (`TuyaBLEDataPoint`, `has_id`, `get_or_create`) (M).
12. Fingerbot button event on the HA bus (S).
13. Climate presets + `hvac_action` heuristic (M).
14. Light `color_type_data` + RGB-encoded color (M).

---

## 9. Map of the actual files touched

| File (hass-localtuya) | change |
|---|---|
| `const.py` | add `CONF_TRANSPORT`, `CONF_BLE_ADDRESS`; relax `DeviceConfig` for missing host |
| `coordinator.py` | `_make_connection`: factory call; keep `update_dps` service working through transport |
| `config_flow.py` | BLE branch in device add step + scan; migrate default transport |
| `discovery.py` | optional BLE scanner function |
| `core/transport/__init__.py` | ABCs + `DPType`/`DPValue`, factory |
| `core/transport/ethernet.py` | wrap `pytuya.TuyaProtocol` |
| `core/transport/bluetooth.py` | adapt `ha_tuya_ble.TuyaBLEDevice` |
| `core/tuya_ble_lib/` | vendored from `ha_tuya_ble/tuya_ble/` + manager |
| `manifest.json` | add `"bluetooth": []` dependency + optional bleak deps |

---

## 10. tldr

- Put the seam at the **semantic DP level**, not the byte-framing level.
- Introduce a `Transport` ABC with `EthernetTransport` (existing pytuya) and `BluetoothTransport` (adapting `ha_tuya_ble.TuyaBLEDevice`) — both expose `set_dps() / status() / update_dps() / keep_alive() / is_connected`.
- Refactor `coordinator.TuyaDevice` to use the factory + interface. The entity layer and 90% of coordinator are transport-agnostic already.
- Vendor `ha_tuya_ble`’s BLE lib and credential manager unchanged; add `bluetooth` HA integration + BLE discovery in config flow.
- The bulk of that is new code is a thin adapter (~100–200 LOC) + config/discovery additions; the hard protocol work stays inside the vendored `tuya_ble_lib` (BLE) and `pytuya` (WiFi) which are already complete.
- **No new cloud layer needed**: both projects already pull DP codes/functions from the same Tuya specs API; the BLE transport just reuses localtuya's existing `dps_data`/cloud for its `code↔dp_id` map.