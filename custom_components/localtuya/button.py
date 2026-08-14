"""Platform to locally control Tuya-based button devices.

Core parity: ``LocalTuyaButton`` mirrors ``homeassistant/components/tuya/button.py``
(``TuyaButtonEntity``).

SYNC CHECKLIST (when the core component is updated):
  1. Diff ``homeassistant/components/tuya/button.py`` against this file.
  2. Port: ``async_press`` and the ``__init__`` wrapper assignment.
  3. Keep our deliberate deltas (they are intentional):
     - transport: writes go over BLE/Ethernet via ``_async_send_wrapper_updates``
       (``_async_send_commands`` sends ``{code, dp_id, value}``) instead of
       cloud MQTT.
     - construction: ``__init__(device, config_entry, dp_id, description=None)``
       resolves the wrapper by dpcode via ``get_button_definition``; the manual
       ``dps`` config (``dp_wrapper_by_id`` / ``RawDPWrapper``) is the fallback
       provider (SPEC_DEFINITION_DRIVEN_RUNTIME.md).
     - ``unique_id`` stays ``local_{device_id}_{dp_id}`` (avoids orphaning).
"""

import logging
from functools import partial
from typing import override

import voluptuous as vol
from homeassistant.components.button import DOMAIN, ButtonEntity

from .entity import LocalTuyaEntity, async_setup_entry
from .const import CONF_PASSIVE_ENTITY
from .core.dp_wrappers import RawDPWrapper, dp_wrapper_by_id
from .core.definitions import get_button_definition

_LOGGER = logging.getLogger(__name__)


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        # vol.Required(CONF_PASSIVE_ENTITY): bool,
    }


class LocalTuyaButton(LocalTuyaEntity, ButtonEntity):
    """Representation of a Tuya button."""

    def __init__(
        self,
        device,
        config_entry,
        buttonid,
        description=None,
        **kwargs,
    ):
        """Initialize the Tuya button."""
        super().__init__(device, config_entry, buttonid, _LOGGER, **kwargs)
        self._state = None
        if description is not None:
            definition = get_button_definition(device, description)
            self._dpcode_wrapper = (
                definition.dpcode_wrapper if definition is not None else None
            )
        else:
            self._dpcode_wrapper = dp_wrapper_by_id(
                self._device, self._dp_id
            ) or RawDPWrapper(self._dp_id)

    @override
    async def async_press(self) -> None:
        """Press the button."""
        await self._async_send_wrapper_updates(self._dpcode_wrapper, True)


async_setup_entry = partial(async_setup_entry, DOMAIN, LocalTuyaButton, flow_schema)
