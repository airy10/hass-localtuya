"""Tests for the integration __init__ (setup/unload)."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

from homeassistant.const import Platform

import custom_components.localtuya as integration
from custom_components.localtuya.const import DOMAIN


async def test_unload_entry_unloads_scene_platform():
    """async_unload_entry must unload the separately-forwarded scene platform."""
    unload = AsyncMock()
    hass = SimpleNamespace(
        data={DOMAIN: {"test_entry": {}}},
        config_entries=SimpleNamespace(async_unload_platforms=unload),
    )
    entry = SimpleNamespace(entry_id="test_entry")

    assert await integration.async_unload_entry(hass, entry) is True

    platforms = unload.call_args.args[1]
    assert Platform.SCENE in platforms
    assert Platform.SWITCH in platforms
    assert "test_entry" not in hass.data[DOMAIN]
