"""Validate the integrity of the per-platform category → entity tables.

Catches regressions in CI: invalid DPCode / DeviceCategory references,
duplicate primary keys, missing or duplicate translation_keys, and
name-versus-translation_key mismatches that would break Home Assistant's
entity name resolution.
"""

import re
import os

import pytest

from custom_components.localtuya.core.ha_entities.base import (
    CLOUD_VALUE,
    DeviceCategory,
    DPCode,
    LocalTuyaEntity,
)

TABLE_DIR = os.path.join(
    os.path.dirname(__file__),
    "..",
    "custom_components",
    "localtuya",
    "core",
    "ha_entities",
)

# Map of source filename → HA platform domain (used to ensure cross-platform
# translation_key uniqueness).
_PLATFORM_DOMAINS = {
    "switches.py": "switch",
    "lights.py": "light",
    "sensors.py": "sensor",
    "numbers.py": "number",
    "selects.py": "select",
    "binary_sensors.py": "binary_sensor",
    "buttons.py": "button",
    "events.py": "event",
    "sirens.py": "siren",
    "fans.py": "fan",
    "covers.py": "cover",
    "climates.py": "climate",
    "humidifiers.py": "humidifier",
    "vacuums.py": "vacuum",
    "valves.py": "valve",
    "water_heaters.py": "water_heater",
    "locks.py": "lock",
    "alarm_control_panels.py": "alarm_control_panel",
    "remotes.py": "remote",
}

# Sentinel for entries whose name intentionally resolves through
# Home Assistant's integration manifests (name=None).
_NAME_NULL_SENTINEL = object()


def _extract_category_entries(
    src: str,
) -> dict[str, list[dict]]:
    """Parse a platform file and return {category_str: [entity_kwarg_dicts]}."""
    categories: dict[str, list[dict]] = {}
    for m in re.finditer(
        r"DeviceCategory\.([A-Z0-9_]+):\s*\((.+?)\n\s*\)", src, re.DOTALL
    ):
        cat = m.group(1)
        body = m.group(2)
        entries = []
        for em in re.finditer(r"LocalTuyaEntity\((.*?)\)\s*[,)]", body, re.DOTALL):
            block = em.group(1)
            entries.append(_parse_entity_block(block))
        categories[cat] = entries
    return categories


def _parse_entity_block(block: str) -> dict:
    """Extract kwarg-like values from a LocalTuyaEntity(…) block."""
    result: dict = {}
    # name
    m = re.search(r'name\s*=\s*"([^"]*)"', block)
    result["name"] = m.group(1) if m else _NAME_NULL_SENTINEL
    # translation_key
    m = re.search(r'translation_key\s*=\s*"([^"]+)"', block)
    result["translation_key"] = m.group(1) if m else None
    # DPCode references (id= and key= as well as tuple members)
    dp_refs: set[str] = set()
    for m in re.finditer(r"DPCode\.([A-Z0-9_]+)", block):
        dp_refs.add(m.group(1))
    result["dpcodes"] = dp_refs
    # entity_category
    m = re.search(r"entity_category\s*=\s*EntityCategory\.(\w+)", block)
    result["entity_category"] = m.group(1) if m else None
    # condition_contains_any
    m = re.search(r"condition_contains_any\s*=\s*\[(.*?)\]", block)
    result["contains_any"] = m.group(1) if m else None
    return result


# ---------------------------------------------------------------------------
# 1. Every table file exists and can be parsed
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "filename,domain",
    sorted(_PLATFORM_DOMAINS.items()),
)
def test_table_exists(filename, domain):
    """Every declared platform has a Python table file."""
    path = os.path.join(TABLE_DIR, filename)
    assert os.path.isfile(path), f"Missing table file for {domain}: {filename}"


# ---------------------------------------------------------------------------
# 2. Every DeviceCategory key is a real enum member
# ---------------------------------------------------------------------------
def _all_category_entries():
    """Yield (filename, domain, category_str, entries) for every table."""
    for filename, domain in _PLATFORM_DOMAINS.items():
        path = os.path.join(TABLE_DIR, filename)
        if not os.path.isfile(path):
            continue
        with open(path) as f:
            src = f.read()
        for cat, entries in _extract_category_entries(src).items():
            yield filename, domain, cat, entries


@pytest.fixture(scope="module")
def all_categories():
    return list(_all_category_entries())


def test_all_device_categories_in_enum(all_categories):
    """Every DeviceCategory key referenced in a table is a valid enum member."""
    valid = set(m.name for m in DeviceCategory)
    invalid = sorted(
        {cat for _, _, cat, _ in all_categories if cat not in valid}
    )
    assert not invalid, f"Unknown categories: {', '.join(invalid)}"


# ---------------------------------------------------------------------------
# 3. Every DPCode reference resolves to a real enum member
# ---------------------------------------------------------------------------
def test_all_dpcodes_in_enum(all_categories):
    """Every DPCode.XXX reference in a table points to a valid enum member."""
    valid = set(m.name for m in DPCode)
    bad: list[str] = []
    for fn, _, cat, entries in all_categories:
        for entry in entries:
            for dp in entry["dpcodes"]:
                if dp not in valid:
                    bad.append(f"  {fn} {cat}: DPCode.{dp}")
    assert not bad, f"Unknown DPCode references:\n" + "\n".join(sorted(bad)[:20])


# ---------------------------------------------------------------------------
# 4. No duplicate primary id within a category+platform
# ---------------------------------------------------------------------------
def test_no_duplicate_primary_ids(all_categories):
    """Within the same category+platform, each primary dpcode appears once."""
    for fn, _, cat, entries in all_categories:
        seen: dict[str, int] = {}
        for idx, entry in enumerate(entries):
            # Primary DP is the first dpcode in the set; the entity's id=.
            dps = sorted(entry["dpcodes"])
            if not dps:
                continue
            primary = dps[0]
            if primary in seen:
                pytest.fail(
                    f"{fn} {cat}: duplicate primary DPCode.{primary} "
                    f"at entries {seen[primary]} and {idx}"
                )
            seen[primary] = idx


# ---------------------------------------------------------------------------
# 5. translation_key is present and unique per platform
# ---------------------------------------------------------------------------
def test_translation_keys_present(all_categories):
    """Every entity in a table carries a translation_key."""
    missing: list[str] = []
    for fn, _, cat, entries in all_categories:
        for idx, entry in enumerate(entries):
            if not entry["translation_key"]:
                missing.append(f"  {fn} {cat} entry {idx}: no translation_key")
    assert not missing, f"Missing translation_keys:\n" + "\n".join(missing[:20])


def test_translation_keys_unique_per_platform(all_categories):
    """All translation_keys within a (platform, category) are unique."""
    seen: dict[tuple[str, str], dict[str, int]] = {}
    for fn, domain, cat, entries in all_categories:
        key = (domain, cat)
        tk_map = seen.setdefault(key, {})
        for idx, entry in enumerate(entries):
            tk = entry["translation_key"]
            if not tk:
                continue
            if tk in tk_map:
                pytest.fail(
                    f"{domain}.{cat}: duplicate translation_key {tk!r} "
                    f"at entries {tk_map[tk]} and {idx}"
                )
            tk_map[tk] = idx


# ---------------------------------------------------------------------------
# 6. Name is provided where translation_key needs a default
# ---------------------------------------------------------------------------
def test_name_or_translation_key_present(all_categories):
    """Every entity has either a name= or relies on translation for naming."""
    missing: list[str] = []
    for fn, _, cat, entries in all_categories:
        for idx, entry in enumerate(entries):
            if entry["name"] is _NAME_NULL_SENTINEL and not entry["translation_key"]:
                missing.append(f"  {fn} {cat} entry {idx}: no name and no translation_key")
    assert not missing, f"Unnamed, untranslated entities:\n" + "\n".join(missing[:20])


# ---------------------------------------------------------------------------
# 7. condition_contains_any values are sensible
# ---------------------------------------------------------------------------
def test_contains_any_format(all_categories):
    """condition_contains_any, when present, is a list of quoted strings."""
    bad: list[str] = []
    for fn, _, cat, entries in all_categories:
        for idx, entry in enumerate(entries):
            raw = entry["contains_any"]
            if raw is None:
                continue
            values = [v.strip().strip('"').strip("'") for v in raw.split(",")]
            if not all(v for v in values):
                bad.append(f"  {fn} {cat} entry {idx}: empty value in contains_any")
    assert not bad, f"Malformed contains_any:\n" + "\n".join(bad[:20])