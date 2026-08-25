"""Platform to present any Tuya DP as a Lock.

No core equivalent: the HA core ``tuya`` integration has no lock platform
(localtuya-only). No sync checklist applies. Keep the manual ``dps`` config
fallback, the description-driven ``__init__`` (SPEC_DEFINITION_DRIVEN_RUNTIME.md),
and the ``lock_state_dp`` / ``jammed_dp`` secondary-DP state machine.
"""

import logging
from functools import partial
from typing import Any
from .config_flow import col_to_select

import voluptuous as vol
from homeassistant.components.lock import DOMAIN, LockEntity
from homeassistant.core import callback
from .entity import LocalTuyaEntity, async_setup_entry

from .const import CONF_JAMMED_DP, CONF_LOCK_STATE_DP
from .core.dp_wrappers import RawDPWrapper, dp_wrapper_by_id
from .core.definitions import get_lock_definition

_LOGGER = logging.getLogger(__name__)


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(CONF_LOCK_STATE_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_JAMMED_DP): col_to_select(dps, is_dps=True),
    }


class LocalTuyaLock(LocalTuyaEntity, LockEntity):
    """Representation of a Tuya Lock."""

    def __init__(
        self,
        device,
        config_entry,
        Lockid,
        description=None,
        **kwargs,
    ):
        """Initialize the Tuya Lock."""
        super().__init__(device, config_entry, Lockid, _LOGGER, **kwargs)
        self._state = None
        # BLE unlock attribution (ported from ha_tuya_ble bea2520).
        self._unlock_dps: dict[int, str] = {}
        self._seen_unlock_dps: set[int] = set()
        if description is not None:
            definition = get_lock_definition(device, description)
            self._dpcode_wrapper = (
                definition.dpcode_wrapper if definition is not None else None
            )
        else:
            self._dpcode_wrapper = dp_wrapper_by_id(
                device, self._dp_id
            ) or RawDPWrapper(self._dp_id)

    async def async_added_to_hass(self):
        """Start tracking who last operated the lock."""
        await super().async_added_to_hass()
        capabilities = self._device.lock_capabilities
        ble_device = self._device.ble_device
        if (
            capabilities is None
            or not capabilities.reports_unlocks
            or ble_device is None
        ):
            return
        self._unlock_dps = dict(capabilities.unlock_records)
        self.async_on_remove(ble_device.register_callback(self._handle_unlock_record))
        self.async_on_remove(
            ble_device.register_disconnected_callback(self._handle_ble_disconnected)
        )

    @callback
    def _handle_ble_disconnected(self) -> None:
        """Expect the replayed status again once the lock comes back."""
        self._seen_unlock_dps.clear()

    @callback
    def _handle_unlock_record(self, datapoints) -> None:
        """Record who opened the lock, for LockEntity.changed_by.

        The first report of each datapoint on a connection is dropped, exactly
        as the unlock event entity drops it: the lock answers a status query
        with the last value of every datapoint, and that value can name a
        credential deleted from the lock hours earlier.
        """
        for datapoint in datapoints:
            method = self._unlock_dps.get(datapoint.id)
            if method is None:
                continue
            if datapoint.id not in self._seen_unlock_dps:
                self._seen_unlock_dps.add(datapoint.id)
                continue
            self._attr_changed_by = f"{method} #{datapoint.value}"
            self.async_write_ha_state()

    async def async_lock(self, **kwargs: Any) -> None:
        """Lock the lock."""
        await self._async_send_wrapper_updates(self._dpcode_wrapper, True)

    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock the lock."""
        await self._async_send_wrapper_updates(self._dpcode_wrapper, False)

    def status_updated(self):
        """Device status was updated."""
        state = self.dp_value(self._dp_id)
        if (lock_state := self.dp_value(CONF_LOCK_STATE_DP)) or lock_state is not None:
            state = lock_state

        self._attr_is_locked = state in (False, "closed", "close", None)

        if jammed := self.dp_value(CONF_JAMMED_DP, False):
            self._attr_is_jammed = jammed

    # No need to restore state for a Lock
    async def restore_state_when_connected(self):
        """Do nothing for a Lock."""
        return


async_setup_entry = partial(async_setup_entry, DOMAIN, LocalTuyaLock, flow_schema)
