# Home Assistant Core Tuya Backport Baseline

Last inspected: 2026-09-04

- Home Assistant core checkout: `$HOME/Sources/Others/homeassistant-core`
- Core commit inspected: `568136f8406f2cd04234e3d0f436ce2983a4564a`
  (`Add local Powerwall control for Teslemetry energy sites (#176969)`)
- Latest Tuya-specific commit inspected in that checkout:
  `5eaeb20bb3fdeb341d279cf2113ce29af38a32e8`
  (`Add Tuya two-channel energy meter sensors and numbers (#178415)`)
- LocalTuya baseline: `6f7d71b2d51de8fd3b570cd1697fe698d565ebe1`

The Tuya component history was reviewed from the last LocalTuya core-table
sync through the latest Tuya-specific changes at the core commit above.
Applicable backports and intentional non-backports should be recorded in the
same change or its final summary.
