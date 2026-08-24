"""Platform to present any Tuya DP as a binary sensor.

Core parity: ``LocalTuyaBinarySensor`` mirrors ``homeassistant/components/tuya/binary_sensor.py``
(``TuyaBinarySensorEntity``).

SYNC CHECKLIST (when the core component is updated):
  1. Diff ``homeassistant/components/tuya/binary_sensor.py`` against this file.
  2. Port: method bodies, ``__init__`` wrapper assignment, and
     ``_process_device_update``.
  3. Keep our deliberate deltas (they are intentional):
     - transport: reads go over BLE/Ethernet via ``_read_wrapper`` instead of
       cloud MQTT.
     - construction: ``__init__(device, config_entry, dp_id, description=None)``
       resolves the wrapper by dpcode via ``get_binary_sensor_definition``; the
       manual ``dps`` config (``dp_wrapper_by_id`` / ``RawDPWrapper``) is the
       fallback provider (SPEC_DEFINITION_DRIVEN_RUNTIME.md).
     - ``unique_id`` stays ``local_{device_id}_{dp_id}`` (avoids orphaning).
     - the on-value comes from ``CONF_STATE_ON`` (the localtuya equivalent of
       core's ``on_value``) and the conversion lives in ``BinarySensorWrapper``;
       ``reset_timer`` is localtuya-only.
"""

import logging
import voluptuous as vol

from functools import partial
from typing import override

from homeassistant.helpers.selector import NumberSelector, NumberSelectorConfig
from homeassistant.helpers.event import async_call_later
from homeassistant.core import callback, CALLBACK_TYPE
from homeassistant.const import CONF_DEVICE_CLASS
from homeassistant.components.binary_sensor import (
    DEVICE_CLASSES_SCHEMA,
    DOMAIN,
    BinarySensorEntity,
)

from .entity import LocalTuyaEntity, async_setup_entry
from .const import CONF_STATE_ON, CONF_RESET_TIMER
from .core.dp_wrappers import RawDPWrapper, dp_wrapper_by_id
from .core.dp_wrapper_decorators import BinarySensorWrapper
from .core.definitions import get_binary_sensor_definition


CONF_STATE_OFF = "state_off"

_LOGGER = logging.getLogger(__name__)


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Required(CONF_STATE_ON, default="true,1,pir,on"): str,
        # vol.Required(CONF_STATE_OFF, default="False"): str,
        vol.Optional(CONF_DEVICE_CLASS): DEVICE_CLASSES_SCHEMA,
        vol.Optional(CONF_RESET_TIMER, default=0): NumberSelector(
            NumberSelectorConfig(min=0, unit_of_measurement="Seconds", mode="box")
        ),
    }


class LocalTuyaBinarySensor(LocalTuyaEntity, BinarySensorEntity):
    """Representation of a Tuya binary sensor."""

    def __init__(
        self,
        device,
        config_entry,
        sensorid,
        description=None,
        **kwargs,
    ):
        """Initialize the Tuya binary sensor."""
        super().__init__(device, config_entry, sensorid, _LOGGER, **kwargs)
        self._reset_override = False

        self._reset_timer: float = self._config.get(CONF_RESET_TIMER, 0)
        self._reset_timer_interval: CALLBACK_TYPE | None = None
        if description is not None:
            definition = get_binary_sensor_definition(device, description)
            self._dpcode_wrapper = (
                definition.dpcode_wrapper if definition is not None else None
            )
        else:
            inner = dp_wrapper_by_id(self._device, self._dp_id) or RawDPWrapper(
                self._dp_id
            )
            self._dpcode_wrapper = BinarySensorWrapper(
                inner, self._config.get(CONF_STATE_ON)
            )

    @property
    @override
    def is_on(self) -> bool | None:
        """Return true if sensor is on."""
        if self._reset_override:
            return False
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
        return not self._dpcode_wrapper.skip_update(
            self._device, updated_status_properties, dp_timestamps
        )

    def status_updated(self):
        """Device status was updated."""
        super().status_updated()

        self._reset_override = False
        if self._reset_timer and self.is_on:
            if self._reset_timer_interval is not None:
                self._reset_timer_interval()
                self._reset_timer_interval = None

            @callback
            def async_reset_state(now):
                """Set the state of the entity to off."""
                # "_update_handler" logic, if status hasn't changed "status_updated" will not be called.
                # Maybe we can find better solution then this workaround?
                self._status[self._dp_id] = "reset_state_binary_sensor"
                self._reset_override = True
                self.async_write_ha_state()

            self._reset_timer_interval = async_call_later(
                self.hass, self._reset_timer, async_reset_state
            )

    @override
    async def async_will_remove_from_hass(self) -> None:
        """Cancel any pending reset timer so it does not fire after removal."""
        if self._reset_timer_interval is not None:
            self._reset_timer_interval()
            self._reset_timer_interval = None

    # No need to restore state for a sensor
    async def restore_state_when_connected(self):
        """Do nothing for a sensor."""
        return


async_setup_entry = partial(
    async_setup_entry, DOMAIN, LocalTuyaBinarySensor, flow_schema
)
