"""Platform to locally control Tuya-based switch devices.

Core parity: ``LocalTuyaSwitch`` mirrors ``homeassistant/components/tuya/switch.py``
(``TuyaSwitchEntity``).

SYNC CHECKLIST (when the core component is updated):
  1. Diff ``homeassistant/components/tuya/switch.py`` against this file.
  2. Port: method bodies, ``__init__`` wrapper assignment, and
     ``_process_device_update``.
  3. Keep our deliberate deltas (they are intentional):
     - transport: reads/writes go over BLE/Ethernet via ``_read_wrapper`` /
       ``_async_send_wrapper_updates`` (``_async_send_commands`` sends
       ``{code, dp_id, value}``) instead of cloud MQTT.
     - construction: ``__init__(device, config_entry, dp_id, description=None)``
       resolves the wrapper by dpcode via ``get_switch_definition``; the manual
       ``dps`` config (``dp_wrapper_by_id`` / ``RawDPWrapper``) is the fallback
       provider (SPEC_DEFINITION_DRIVEN_RUNTIME.md).
     - ``unique_id`` stays ``local_{device_id}_{dp_id}`` (avoids orphaning).
     - ``bitmap_mask`` writes and restore-on-reconnect are localtuya-only.
       (current/voltage/power are sensor entities, as in core — see
       ``core/ha_entities/sensors.py``.)
"""

import logging
from functools import partial
from typing import Any, override

from .config_flow import col_to_select

import voluptuous as vol
from homeassistant.components.switch import (
    DOMAIN,
    SwitchEntity,
    DEVICE_CLASSES_SCHEMA,
    SwitchDeviceClass,
)
from homeassistant.const import CONF_DEVICE_CLASS

from .entity import LocalTuyaEntity, async_setup_entry
from .core.definitions import get_switch_definition
from .core.dp_wrappers import BitmapMaskWrapper, RawDPWrapper, dp_wrapper_by_id
from .const import (
    CONF_BITMAP_MASK,
    CONF_DEFAULT_VALUE,
    CONF_PASSIVE_ENTITY,
    CONF_RESTORE_ON_RECONNECT,
)

_LOGGER = logging.getLogger(__name__)


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Required(CONF_RESTORE_ON_RECONNECT): bool,
        vol.Required(CONF_PASSIVE_ENTITY): bool,
        vol.Optional(CONF_DEFAULT_VALUE): str,
        vol.Optional(CONF_BITMAP_MASK): str,
        vol.Optional(CONF_DEVICE_CLASS): col_to_select(
            [sc.value for sc in SwitchDeviceClass]
        ),
    }


class LocalTuyaSwitch(LocalTuyaEntity, SwitchEntity):
    """Representation of a Tuya switch."""

    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(
        self,
        device,
        config_entry,
        switchid,
        description=None,
        **kwargs,
    ):
        """Initialize the Tuya switch.

        When ``description`` (a ``LocalTuyaEntity`` from the category tables)
        is given, the wrapper is resolved by dpcode via ``get_switch_definition``;
        otherwise the manual config-driven ``dps`` path is used.
        """
        super().__init__(device, config_entry, switchid, _LOGGER, **kwargs)
        self._state = None
        self._bitmap_mask = self._parse_bitmap_mask()

        if description is not None:
            definition = get_switch_definition(device, description)
            wrapper = definition.switch_wrapper if definition is not None else None
        else:
            wrapper = dp_wrapper_by_id(device, self._dp_id) or RawDPWrapper(self._dp_id)

        if self._bitmap_mask and wrapper is not None:
            wrapper = BitmapMaskWrapper(wrapper, self._bitmap_mask)
        self._dpcode_wrapper = wrapper

    def _parse_bitmap_mask(self) -> bytes | None:
        """Parse the configured bitmap mask (hex string) into bytes."""
        mask = self._config.get(CONF_BITMAP_MASK)
        if not mask:
            return None
        try:
            return bytes.fromhex(mask)
        except ValueError:
            _LOGGER.warning(
                "Invalid bitmap_mask %r for %s, ignoring", mask, self.name
            )
            return None

    @property
    @override
    def is_on(self) -> bool | None:
        """Return true if switch is on."""
        return self._read_wrapper(self._dpcode_wrapper)

    @override
    async def _process_device_update(
        self,
        updated_status_properties: list[str],
        dp_timestamps: dict[str, int] | None,
    ) -> bool:
        """Called when Tuya device sends an update with updated properties.

        Returns True if the Home Assistant state should be written,
        or False if the state write should be skipped.
        """
        if self._dpcode_wrapper is None:
            return True
        return not self._dpcode_wrapper.skip_update(
            self._device, updated_status_properties, dp_timestamps
        )

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self._async_send_wrapper_updates(self._dpcode_wrapper, True)

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self._async_send_wrapper_updates(self._dpcode_wrapper, False)

    # Default value is the "OFF" state
    def entity_default_value(self):
        """Return False as the default value for this entity type."""
        return False


async_setup_entry = partial(async_setup_entry, DOMAIN, LocalTuyaSwitch, flow_schema)
