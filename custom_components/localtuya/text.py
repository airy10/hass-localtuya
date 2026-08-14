"""Platform to present any Tuya DP as a text.

No core equivalent: the HA core ``tuya`` integration has no text platform
(localtuya-only). No sync checklist applies. Keep the manual ``dps`` config
fallback and the description-driven ``__init__``
(SPEC_DEFINITION_DRIVEN_RUNTIME.md).
"""

import logging
from functools import partial

import voluptuous as vol
from homeassistant.components.text import DOMAIN, TextEntity
from homeassistant.const import STATE_UNKNOWN

from .entity import LocalTuyaEntity, async_setup_entry
from .const import (
    CONF_DEFAULT_VALUE,
    CONF_PASSIVE_ENTITY,
    CONF_PATTERN,
    CONF_RESTORE_ON_RECONNECT,
)

_LOGGER = logging.getLogger(__name__)


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(CONF_RESTORE_ON_RECONNECT, default=False): bool,
        vol.Optional(CONF_PASSIVE_ENTITY, default=False): bool,
        vol.Optional(CONF_DEFAULT_VALUE): str,
        vol.Optional(CONF_PATTERN): str,
    }


class LocalTuyaText(LocalTuyaEntity, TextEntity):
    """Representation of a Tuya Text."""

    def __init__(
        self,
        device,
        config_entry,
        sensorid,
        **kwargs,
    ):
        """Initialize the Tuya text."""
        super().__init__(device, config_entry, sensorid, _LOGGER, **kwargs)
        self._state = STATE_UNKNOWN

    @property
    def native_value(self) -> str | None:
        """Return the value reported by the text."""
        state = self.dp_value(self._dp_id)
        if state is None:
            return None
        return str(state)

    @property
    def pattern(self) -> str | None:
        """Return the regex pattern that the value must match."""
        return self._config.get(CONF_PATTERN)

    async def async_set_value(self, value: str) -> None:
        """Change the value."""
        await self._device.set_dp(value, self._dp_id)

    # Default value is an empty string
    def entity_default_value(self):
        """Return the default value for this entity type."""
        return ""


async_setup_entry = partial(async_setup_entry, DOMAIN, LocalTuyaText, flow_schema)