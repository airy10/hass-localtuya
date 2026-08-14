"""Platform to present any Tuya DP as a number."""

import logging
from functools import partial

import voluptuous as vol
from homeassistant.components.number import DOMAIN, NumberEntity, DEVICE_CLASSES_SCHEMA
from homeassistant.const import (
    CONF_DEVICE_CLASS,
    STATE_UNKNOWN,
    CONF_UNIT_OF_MEASUREMENT,
)

from .entity import LocalTuyaEntity, async_setup_entry
from .const import (
    CONF_DEFAULT_VALUE,
    CONF_MAX_VALUE,
    CONF_MIN_VALUE,
    CONF_OFFSET,
    CONF_PASSIVE_ENTITY,
    CONF_RESTORE_ON_RECONNECT,
    CONF_SCALING,
    CONF_STEPSIZE,
)
from .core.dp_wrappers import RawDPWrapper, dp_wrapper_by_id

_LOGGER = logging.getLogger(__name__)

DEFAULT_MIN = 0
DEFAULT_MAX = 100000
DEFAULT_STEP = 1.0


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(CONF_MIN_VALUE, default=DEFAULT_MIN): vol.All(
            vol.Coerce(float),
            vol.Range(min=-1000000.0, max=1000000.0),
        ),
        vol.Required(CONF_MAX_VALUE, default=DEFAULT_MAX): vol.All(
            vol.Coerce(float),
            vol.Range(min=-1000000.0, max=1000000.0),
        ),
        vol.Required(CONF_STEPSIZE, default=DEFAULT_STEP): vol.All(
            vol.Coerce(float), vol.Range(min=0.0, max=1000000.0)
        ),
        vol.Optional(CONF_RESTORE_ON_RECONNECT, default=False): bool,
        vol.Optional(CONF_PASSIVE_ENTITY, default=False): bool,
        vol.Optional(CONF_DEFAULT_VALUE): str,
        vol.Optional(CONF_DEVICE_CLASS): DEVICE_CLASSES_SCHEMA,
        vol.Optional(CONF_UNIT_OF_MEASUREMENT): vol.Any(None, str),
        vol.Optional(CONF_SCALING): vol.All(
            vol.Coerce(float), vol.Range(min=-1000000.0, max=1000000.0)
        ),
        vol.Optional(CONF_OFFSET): vol.All(
            vol.Coerce(float), vol.Range(min=-1000000.0, max=1000000.0)
        ),
    }


class LocalTuyaNumber(LocalTuyaEntity, NumberEntity):
    """Representation of a Tuya Number."""

    def __init__(
        self,
        device,
        config_entry,
        sensorid,
        **kwargs,
    ):
        """Initialize the Tuya sensor."""
        super().__init__(device, config_entry, sensorid, _LOGGER, **kwargs)
        self._state = STATE_UNKNOWN

        self._dpcode_wrapper = dp_wrapper_by_id(self._device, self._dp_id) or RawDPWrapper(
            self._dp_id
        )
        wrapper = self._dpcode_wrapper

        if CONF_MIN_VALUE in self._config:
            self._min_value = self.scale(self._config[CONF_MIN_VALUE])
        else:
            self._min_value = (
                wrapper.min_value
                if wrapper.min_value is not None
                else self.scale(DEFAULT_MIN)
            )
        if CONF_MAX_VALUE in self._config:
            self._max_value = self.scale(self._config[CONF_MAX_VALUE])
        else:
            self._max_value = (
                wrapper.max_value
                if wrapper.max_value is not None
                else self.scale(DEFAULT_MAX)
            )
        if CONF_STEPSIZE in self._config:
            self._step_size = self.scale(
                self._config[CONF_STEPSIZE], scale_only=True
            )
        else:
            self._step_size = (
                wrapper.value_step
                if wrapper.value_step is not None
                else self.scale(DEFAULT_STEP, scale_only=True)
            )

        # Override standard default value handling to cast to a float
        default_value = self._config.get(CONF_DEFAULT_VALUE)
        if default_value is not None:
            self._default_value = float(default_value)

    @property
    def native_value(self) -> float:
        """Return the entity value to represent the entity state."""
        if not self._config.get(CONF_OFFSET) and not self._config.get(CONF_SCALING):
            return self._read_wrapper(self._dpcode_wrapper)
        self._state = self.scale(self._state)
        return self._state

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

    @property
    def native_min_value(self) -> float:
        """Return the minimum value."""
        return self._min_value

    @property
    def native_max_value(self) -> float:
        """Return the maximum value."""
        return self._max_value

    @property
    def native_step(self) -> float:
        """Return the maximum value."""
        return self._step_size

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return self._config.get(CONF_UNIT_OF_MEASUREMENT)

    @property
    def device_class(self):
        """Return the class of this device."""
        return self._config.get(CONF_DEVICE_CLASS)

    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""
        if not self._config.get(CONF_OFFSET) and not self._config.get(CONF_SCALING):
            await self._async_send_wrapper_updates(self._dpcode_wrapper, value)
            return
        offset = self._config.get(CONF_OFFSET)
        if offset is not None:
            value = value - offset
        if scale_factor := self._config.get(CONF_SCALING):
            value = value / float(scale_factor)

        await self._device.set_dp(int(value), self._dp_id)

    # Default value is the minimum value
    def entity_default_value(self):
        """Return the minimum value as the default for this entity type."""
        return self._min_value


async_setup_entry = partial(async_setup_entry, DOMAIN, LocalTuyaNumber, flow_schema)
