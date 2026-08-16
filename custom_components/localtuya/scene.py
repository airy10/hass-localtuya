"""Support for Tuya scenes.

Core parity: ``TuyaSceneEntity`` mirrors ``homeassistant/components/tuya/scene.py``.

SYNC CHECKLIST (when the core component is updated):
  1. Diff ``homeassistant/components/tuya/scene.py`` against this file.
  2. Port: ``async_activate``, ``unique_id`` (``tys{scene_id}``), availability.
  3. Keep our deliberate deltas (they are intentional):
     - scenes are cloud-only (``SharingCloud.async_get_scenes`` /
       ``async_trigger_scene``); the legacy ``TuyaCloudApi`` has no scene
       endpoint and localtuya has no local scene DP.
"""

import logging
from typing import Any, override

from homeassistant.components.scene import Scene
from homeassistant.const import CONF_DEVICE_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import HassLocalTuyaData
from .core.sharing_cloud import SharingCloud

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tuya scenes from the sharing cloud session.

    Scenes are only available through the Smart Life sharing session
    (``SharingCloud``); the legacy IoT-Platform ``TuyaCloudApi`` has no scene
    endpoint, in which case this platform registers nothing.
    """
    hass_entry_data: HassLocalTuyaData = hass.data[DOMAIN][config_entry.entry_id]
    cloud_data = hass_entry_data.cloud_data
    if not isinstance(cloud_data, SharingCloud):
        return

    scenes = await cloud_data.async_get_scenes()
    if scenes:
        async_add_entities(
            TuyaSceneEntity(cloud_data, scene, config_entry.entry_id)
            for scene in scenes
        )


class TuyaSceneEntity(Scene):
    """Tuya Scene Remote."""

    _should_poll = False
    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, cloud_data: SharingCloud, scene, entry_id: str) -> None:
        """Init Tuya Scene."""
        super().__init__()
        self._attr_unique_id = f"tys{scene.scene_id}"
        self._cloud_data = cloud_data
        self.scene = scene
        self._entry_id = entry_id

    @property
    @override
    def device_info(self) -> DeviceInfo:
        """Return a device description for device registry."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self.unique_id}")},
            manufacturer="tuya",
            name=self.scene.name,
            model="Tuya Scene",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    @override
    def available(self) -> bool:
        """Return if the scene is enabled."""
        return self.scene.enabled

    @override
    async def async_activate(self, **kwargs: Any) -> None:
        """Activate the scene."""
        await self._cloud_data.async_trigger_scene(
            self.scene.home_id, self.scene.scene_id
        )
