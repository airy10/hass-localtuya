"""Platform to locally control Tuya-based switch devices."""

import logging
from functools import partial
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
from .core.dp_wrappers import BitmapMaskWrapper, RawDPWrapper, dp_wrapper_by_id
from .const import (
    ATTR_CURRENT,
    ATTR_CURRENT_CONSUMPTION,
    ATTR_STATE,
    ATTR_VOLTAGE,
    CONF_BITMAP_MASK,
    CONF_CURRENT,
    CONF_CURRENT_CONSUMPTION,
    CONF_DEFAULT_VALUE,
    CONF_PASSIVE_ENTITY,
    CONF_RESTORE_ON_RECONNECT,
    CONF_VOLTAGE,
)

_LOGGER = logging.getLogger(__name__)


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(CONF_CURRENT): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_CURRENT_CONSUMPTION): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_VOLTAGE): col_to_select(dps, is_dps=True),
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
        **kwargs,
    ):
        """Initialize the Tuya switch."""
        super().__init__(device, config_entry, switchid, _LOGGER, **kwargs)
        self._state = None
        self._bitmap_mask = self._parse_bitmap_mask()
        wrapper = dp_wrapper_by_id(device, self._dp_id) or RawDPWrapper(self._dp_id)
        if self._bitmap_mask:
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
    def is_on(self):
        """Return true if switch is on."""
        return self._read_wrapper(self._dpcode_wrapper)

    @property
    def extra_state_attributes(self):
        """Return device state attributes."""
        attrs = {}
        if self.has_config(CONF_CURRENT):
            attrs[ATTR_CURRENT] = self.dp_value(self._config[CONF_CURRENT])
        if self.has_config(CONF_CURRENT_CONSUMPTION):
            val_cc = self.dp_value(self._config[CONF_CURRENT_CONSUMPTION])
            attrs[ATTR_CURRENT_CONSUMPTION] = None if val_cc is None else val_cc / 10
        if self.has_config(CONF_VOLTAGE):
            val_vol = self.dp_value(self._config[CONF_VOLTAGE])
            attrs[ATTR_VOLTAGE] = None if val_vol is None else val_vol / 10

        # Store the state
        if self._state is not None:
            attrs[ATTR_STATE] = self._state
        elif self._last_state is not None:
            attrs[ATTR_STATE] = self._last_state
        return attrs

    async def _process_device_update(
        self,
        updated_status_properties: list[str],
        dp_timestamps: dict[str, int] | None,
    ) -> bool:
        """Called when Tuya device sends an update with updated properties.

        Returns True if the Home Assistant state should be written,
        or False if the state write should be skipped.
        """
        return not self._dpcode_wrapper.skip_update(
            self._device, updated_status_properties, dp_timestamps
        )

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        await self._async_send_wrapper_updates(self._dpcode_wrapper, True)

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        await self._async_send_wrapper_updates(self._dpcode_wrapper, False)

    # Default value is the "OFF" state
    def entity_default_value(self):
        """Return False as the default value for this entity type."""
        return False


async_setup_entry = partial(async_setup_entry, DOMAIN, LocalTuyaSwitch, flow_schema)
