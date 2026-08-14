"""Platform to present any Tuya DP as a siren.

Core parity: ``LocalTuyaSiren`` mirrors ``homeassistant/components/tuya/siren.py``
(``TuyaSirenEntity``).

SYNC CHECKLIST (when the core component is updated):
  1. Diff ``homeassistant/components/tuya/siren.py`` against this file.
  2. Port: method bodies, ``__init__`` wrapper assignment, and
     ``_process_device_update``.
  3. Keep our deliberate deltas (they are intentional):
     - transport: reads/writes go over BLE/Ethernet via ``_read_wrapper`` /
       ``_async_send_wrapper_updates`` (``_async_send_commands`` sends
       ``{code, dp_id, value}``) instead of cloud MQTT.
     - construction: ``__init__(device, config_entry, dp_id, description=None)``
       resolves the wrapper by dpcode via ``get_siren_definition``; the manual
       ``dps`` config (``dp_wrapper_by_id`` / ``RawDPWrapper``) is the fallback
       provider (SPEC_DEFINITION_DRIVEN_RUNTIME.md).
     - ``unique_id`` stays ``local_{device_id}_{dp_id}`` (avoids orphaning).
     - ``is_on`` keeps a bool-guard (the raw DP may be a string for
       non-boolean wirings).
"""

import logging
from functools import partial
from typing import Any, override

import voluptuous as vol
from homeassistant.components.siren import DOMAIN, SirenEntity, SirenEntityFeature

from .entity import LocalTuyaEntity, async_setup_entry
from .const import CONF_STATE_ON
from .core.dp_wrappers import RawDPWrapper, dp_wrapper_by_id
from .core.definitions import get_siren_definition

_LOGGER = logging.getLogger(__name__)

# CONF_STATE_MAP = ["True and False", "ON and OFF"]


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Required(CONF_STATE_ON, default="true"): str,
        # vol.Required(CONF_STATE_OFF, default="False"): str,
    }


class LocalTuyaSiren(LocalTuyaEntity, SirenEntity):
    """Representation of a Tuya siren."""

    _attr_supported_features = SirenEntityFeature.TURN_ON | SirenEntityFeature.TURN_OFF

    def __init__(
        self,
        device,
        config_entry,
        sirenid,
        description=None,
        **kwargs,
    ):
        """Initialize the Tuya siren."""
        super().__init__(device, config_entry, sirenid, _LOGGER, **kwargs)
        self._is_on = False
        if description is not None:
            definition = get_siren_definition(device, description)
            self._dpcode_wrapper = (
                definition.dpcode_wrapper if definition is not None else None
            )
        else:
            self._dpcode_wrapper = dp_wrapper_by_id(
                self._device, self._dp_id
            ) or RawDPWrapper(self._dp_id)

    @property
    @override
    def is_on(self) -> bool | None:
        """Return true if siren is on."""
        state = self._read_wrapper(self._dpcode_wrapper)
        if isinstance(state, bool):
            return state
        return self._is_on

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
        return not self._dpcode_wrapper.skip_update(
            self._device, updated_status_properties, dp_timestamps
        )

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the siren on."""
        await self._async_send_wrapper_updates(self._dpcode_wrapper, True)

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the siren off."""
        await self._async_send_wrapper_updates(self._dpcode_wrapper, False)

    # No need to restore state for a siren
    async def restore_state_when_connected(self):
        """Do nothing for a siren."""
        return

    def status_updated(self):
        """Device status was updated."""
        super().status_updated()

        state = str(self.dp_value(self._dp_id)).lower()
        if state == self._config[CONF_STATE_ON].lower() or state == "true":
            self._is_on = True
        else:
            self._is_on = False


async_setup_entry = partial(async_setup_entry, DOMAIN, LocalTuyaSiren, flow_schema)
