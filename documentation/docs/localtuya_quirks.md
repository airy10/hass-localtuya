# Custom quirks

Some Tuya products ship buggy or incomplete DP metadata in the cloud catalog (wrong types, missing ranges, wrong dp ids). LocalTuya ships built-in fixes for the known cases in a product-id keyed quirks registry — the same mechanism as HA core's `tuya_device_handlers` quirks.

You can add your own fixes without editing the component: put Python files into a `localtuya_quirks` folder inside your Home Assistant configuration directory:

```text
/config/localtuya_quirks/my_quirk.py
```

Every `.py` file in that folder is imported once at integration startup. At import time, register a quirk with the same builder API the built-in quirks use:

```python
from custom_components.localtuya.core.quirks import (
    DPMode,
    QUIRKS_REGISTRY,
    DeviceQuirk,
)

DeviceQuirk().applies_to(product_id="xxxxxxxx") \
    .add_dpid_integer(
        dpid=3,
        dpcode="countdown",
        dpmode=DPMode.READ | DPMode.WRITE,
        unit="s",
        min=0,
        max=86400,
        scale=1,
        step=60,
    ) \
    .register(QUIRKS_REGISTRY)
```

Notes:

- `product_id` is the device's cloud product id (visible in diagnostics and in the device's cloud data).
- Quirks are applied to the device spec (`function` / `status_range` / category) *before* entities resolve their wrappers — so a quirk can fix or add the DP metadata that entity auto-configuration relies on.
- Deleting a file and restarting (or reloading the integration) removes its quirks again; a broken module is logged at startup but never blocks the integration.
- The folder mirrors HA core's `config/tuya_quirks/` mechanism; if you have written quirks for core before, the builder API is the same.
