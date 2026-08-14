"""Platform to locally control Tuya-based fan devices."""

import logging
from functools import partial
from .config_flow import col_to_select

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.fan import (
    DOMAIN,
    FanEntityFeature,
    FanEntity,
)
from homeassistant.util.percentage import int_states_in_range

from .entity import LocalTuyaEntity, async_setup_entry
from .core.dp_wrappers import RawDPWrapper, dp_wrapper_by_id
from .core.dp_wrapper_decorators import (
    FanDirectionWrapper,
    FanSpeedPercentageWrapper,
)
from .const import (
    CONF_FAN_DIRECTION,
    CONF_FAN_DIRECTION_FWD,
    CONF_FAN_DIRECTION_REV,
    CONF_FAN_DPS_TYPE,
    CONF_FAN_ORDERED_LIST,
    CONF_FAN_OSCILLATING_CONTROL,
    CONF_FAN_SPEED_CONTROL,
    CONF_FAN_SPEED_MAX,
    CONF_FAN_SPEED_MIN,
)

_LOGGER = logging.getLogger(__name__)


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(CONF_FAN_SPEED_CONTROL): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_FAN_OSCILLATING_CONTROL): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_FAN_DIRECTION): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_FAN_DIRECTION_FWD, default="forward"): cv.string,
        vol.Optional(CONF_FAN_DIRECTION_REV, default="reverse"): cv.string,
        vol.Optional(CONF_FAN_SPEED_MIN, default=1): cv.positive_int,
        vol.Optional(CONF_FAN_SPEED_MAX, default=9): cv.positive_int,
        vol.Optional(CONF_FAN_ORDERED_LIST, default="disabled"): cv.string,
        # vol.Optional(CONF_FAN_DPS_TYPE, default="str"): vol.In(["str", "int"]),
    }


class LocalTuyaFan(LocalTuyaEntity, FanEntity):
    """Representation of a Tuya fan."""

    def __init__(
        self,
        device,
        config_entry,
        fanid,
        **kwargs,
    ):
        """Initialize the entity."""
        super().__init__(device, config_entry, fanid, _LOGGER, **kwargs)
        self._speed_range = (
            int(self._config.get(CONF_FAN_SPEED_MIN, 1)),
            int(self._config.get(CONF_FAN_SPEED_MAX, 9)),
        )
        self._ordered_list = self._config.get(CONF_FAN_ORDERED_LIST).split(",")

        if isinstance(self._ordered_list, list) and len(self._ordered_list) > 1:
            self._use_ordered_list = True
        else:
            self._use_ordered_list = False

        # Cloud spec wrappers for the configured DPs (core parity); DPs with
        # no cloud spec fall back to a raw wrapper so reads/writes always
        # delegate through the wrapper layer. Speed/direction conversion lives
        # in the decorators, keeping the entity thin.
        self._switch_wrapper = dp_wrapper_by_id(
            device, self._dp_id
        ) or RawDPWrapper(self._dp_id)

        speed_dp = self._config.get(CONF_FAN_SPEED_CONTROL)
        if self.has_config(CONF_FAN_SPEED_CONTROL):
            inner = dp_wrapper_by_id(device, speed_dp) or RawDPWrapper(speed_dp)
            self._speed_wrapper = FanSpeedPercentageWrapper(
                inner,
                self._speed_range,
                self._ordered_list if self._use_ordered_list else None,
            )
        else:
            self._speed_wrapper = None

        osc_dp = self._config.get(CONF_FAN_OSCILLATING_CONTROL)
        self._oscillate_wrapper = (
            dp_wrapper_by_id(device, osc_dp) or RawDPWrapper(osc_dp)
        ) if self.has_config(CONF_FAN_OSCILLATING_CONTROL) else None

        dir_dp = self._config.get(CONF_FAN_DIRECTION)
        if self.has_config(CONF_FAN_DIRECTION):
            inner = dp_wrapper_by_id(device, dir_dp) or RawDPWrapper(dir_dp)
            self._direction_wrapper = FanDirectionWrapper(
                inner,
                self._config.get(CONF_FAN_DIRECTION_FWD),
                self._config.get(CONF_FAN_DIRECTION_REV),
            )
        else:
            self._direction_wrapper = None

    async def async_set_direction(self, direction):
        """Set the direction of the fan."""
        await self._async_send_wrapper_updates(self._direction_wrapper, direction)
        self.schedule_update_ha_state()

    async def async_set_percentage(self, percentage):
        """Set the speed of the fan, as a percentage."""
        if percentage is not None:
            if percentage == 0:
                return await self.async_turn_off()
            if not self.is_on:
                await self.async_turn_on()
            await self._async_send_wrapper_updates(self._speed_wrapper, percentage)
            self.schedule_update_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the fan off."""
        await self._async_send_wrapper_updates(self._switch_wrapper, False)
        self.schedule_update_ha_state()

    async def async_turn_on(
        self,
        speed: str = None,
        percentage: int = None,
        preset_mode: str = None,
        **kwargs,
    ) -> None:
        """Turn on the fan."""
        await self._async_send_wrapper_updates(self._switch_wrapper, True)
        if percentage is not None:
            await self.async_set_percentage(percentage)
        else:
            self.schedule_update_ha_state()

    async def async_oscillate(self, oscillating: bool) -> None:
        """Oscillate the fan."""
        await self._async_send_wrapper_updates(self._oscillate_wrapper, oscillating)
        self.schedule_update_ha_state()

    @property
    def is_on(self):
        """Return true if fan is on."""
        return self._read_wrapper(self._switch_wrapper)

    @property
    def current_direction(self):
        """Return the current direction of the fan."""
        return self._read_wrapper(self._direction_wrapper)

    @property
    def oscillating(self):
        """Return true if the fan is oscillating."""
        return self._read_wrapper(self._oscillate_wrapper)

    @property
    def percentage(self):
        """Return the current speed."""
        return self._read_wrapper(self._speed_wrapper)

    @property
    def supported_features(self) -> FanEntityFeature:
        """Flag supported features."""
        features = FanEntityFeature(0)

        if self._oscillate_wrapper is not None:
            features |= FanEntityFeature.OSCILLATE

        if self._speed_wrapper is not None:
            features |= FanEntityFeature.SET_SPEED

        if self._direction_wrapper is not None:
            features |= FanEntityFeature.DIRECTION

        features |= FanEntityFeature.TURN_OFF
        features |= FanEntityFeature.TURN_ON

        return features

    @property
    def speed_count(self) -> int:
        """Speed count for the fan."""
        if self._use_ordered_list:
            return len(self._ordered_list)
        return int_states_in_range(self._speed_range)


async_setup_entry = partial(async_setup_entry, DOMAIN, LocalTuyaFan, flow_schema)
