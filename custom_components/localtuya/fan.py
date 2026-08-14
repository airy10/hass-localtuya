"""Platform to locally control Tuya-based fan devices."""

import logging
import math
from functools import partial
from .config_flow import col_to_select

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.fan import (
    DIRECTION_FORWARD,
    DIRECTION_REVERSE,
    DOMAIN,
    FanEntityFeature,
    FanEntity,
)
from homeassistant.util.percentage import (
    int_states_in_range,
    ordered_list_item_to_percentage,
    percentage_to_ordered_list_item,
    percentage_to_ranged_value,
    ranged_value_to_percentage,
)

from .entity import LocalTuyaEntity, async_setup_entry
from .core.dp_wrappers import RawDPWrapper, dp_wrapper_by_id
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
        self._is_on = False
        self._oscillating = None
        self._direction = None
        self._percentage = None
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
        # delegate through the wrapper layer.
        self._switch_wrapper = dp_wrapper_by_id(
            device, self._dp_id
        ) or RawDPWrapper(self._dp_id)
        self._speed_wrapper = (
            dp_wrapper_by_id(device, self._config.get(CONF_FAN_SPEED_CONTROL))
            or RawDPWrapper(self._config.get(CONF_FAN_SPEED_CONTROL))
        ) if self.has_config(CONF_FAN_SPEED_CONTROL) else None
        self._oscillate_wrapper = (
            dp_wrapper_by_id(device, self._config.get(CONF_FAN_OSCILLATING_CONTROL))
            or RawDPWrapper(self._config.get(CONF_FAN_OSCILLATING_CONTROL))
        ) if self.has_config(CONF_FAN_OSCILLATING_CONTROL) else None
        self._direction_wrapper = (
            dp_wrapper_by_id(device, self._config.get(CONF_FAN_DIRECTION))
            or RawDPWrapper(self._config.get(CONF_FAN_DIRECTION))
        ) if self.has_config(CONF_FAN_DIRECTION) else None

    async def async_set_direction(self, direction):
        """Set the direction of the fan."""
        _LOGGER.debug("Fan async_set_direction: %s", direction)

        if direction == DIRECTION_FORWARD:
            value = self._config.get(CONF_FAN_DIRECTION_FWD)

        if direction == DIRECTION_REVERSE:
            value = self._config.get(CONF_FAN_DIRECTION_REV)
        await self._async_send_wrapper_updates(self._direction_wrapper, value)
        self.schedule_update_ha_state()

    async def async_set_percentage(self, percentage):
        """Set the speed of the fan, as a percentage."""
        _LOGGER.debug("Fan async_set_percentage: %s", percentage)

        if percentage is not None:
            if percentage == 0:
                return await self.async_turn_off()
            if not self.is_on:
                await self.async_turn_on()

            if self._use_ordered_list:
                value = str(
                    percentage_to_ordered_list_item(self._ordered_list, percentage)
                )
                _LOGGER.debug(
                    "Fan async_set_percentage: %s > %s", percentage, value
                )
            else:
                value = int(
                    math.ceil(
                        percentage_to_ranged_value(self._speed_range, percentage)
                    )
                )
                _LOGGER.debug(
                    "Fan async_set_percentage: %s > %s", percentage, value
                )
            await self._async_send_wrapper_updates(self._speed_wrapper, value)
            self.schedule_update_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the fan off."""
        _LOGGER.debug("Fan async_turn_off")

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
        _LOGGER.debug("Fan async_turn_on")
        await self._async_send_wrapper_updates(self._switch_wrapper, True)
        if percentage is not None:
            await self.async_set_percentage(percentage)
        else:
            self.schedule_update_ha_state()

    async def async_oscillate(self, oscillating: bool) -> None:
        """Oscillate the fan."""
        _LOGGER.debug("Fan async_oscillate: %s", oscillating)
        await self._async_send_wrapper_updates(self._oscillate_wrapper, oscillating)
        self.schedule_update_ha_state()

    @property
    def is_on(self):
        """Return true if fan is on."""
        return self._read_wrapper(self._switch_wrapper)

    @property
    def current_direction(self):
        """Return the current direction of the fan."""
        value = self._read_wrapper(self._direction_wrapper)
        if value is not None:
            if value == self._config.get(CONF_FAN_DIRECTION_FWD):
                return DIRECTION_FORWARD
            if value == self._config.get(CONF_FAN_DIRECTION_REV):
                return DIRECTION_REVERSE
        return self._direction

    @property
    def oscillating(self):
        """Return true if the fan is oscillating."""
        return self._read_wrapper(self._oscillate_wrapper)

    @property
    def percentage(self):
        """Return the current speed."""
        speed = self._read_wrapper(self._speed_wrapper)
        if speed is not None:
            if self._use_ordered_list:
                if str(speed) in self._ordered_list:
                    return ordered_list_item_to_percentage(
                        self._ordered_list, str(speed)
                    )
            else:
                return ranged_value_to_percentage(
                    self._speed_range, int(speed)
                )
        return self._percentage

    @property
    def supported_features(self) -> FanEntityFeature:
        """Flag supported features."""
        features = FanEntityFeature(0)

        if self.has_config(CONF_FAN_OSCILLATING_CONTROL):
            features |= FanEntityFeature.OSCILLATE

        if self.has_config(CONF_FAN_SPEED_CONTROL):
            features |= FanEntityFeature.SET_SPEED

        if self.has_config(CONF_FAN_DIRECTION):
            features |= FanEntityFeature.DIRECTION

        features |= FanEntityFeature.TURN_OFF
        features |= FanEntityFeature.TURN_ON

        return features

    @property
    def speed_count(self) -> int:
        """Speed count for the fan."""
        if self._use_ordered_list:
            return len(self._ordered_list)
        speed_count = int_states_in_range(self._speed_range)
        _LOGGER.debug("Fan speed_count: %s", speed_count)
        return speed_count

    def status_updated(self):
        """Get state of Tuya fan."""
        self._is_on = self.dp_value(self._dp_id)

        current_speed = self.dp_value(CONF_FAN_SPEED_CONTROL)
        if self._use_ordered_list:
            _LOGGER.debug(
                "Fan current_speed ordered_list_item_to_percentage: %s from %s",
                current_speed,
                self._ordered_list,
            )
            if current_speed is not None:
                if str(current_speed) not in self._ordered_list:
                    self._percentage = None
                else:
                    self._percentage = ordered_list_item_to_percentage(
                        self._ordered_list, str(current_speed)
                    )
        else:
            _LOGGER.debug(
                "Fan current_speed ranged_value_to_percentage: %s from %s",
                current_speed,
                self._speed_range,
            )
            if current_speed is not None:
                self._percentage = ranged_value_to_percentage(
                    self._speed_range, int(current_speed)
                )

        _LOGGER.debug("Fan current_percentage: %s", self._percentage)

        if self.has_config(CONF_FAN_OSCILLATING_CONTROL):
            self._oscillating = self.dp_value(CONF_FAN_OSCILLATING_CONTROL)
            _LOGGER.debug("Fan current_oscillating : %s", self._oscillating)

        if self.has_config(CONF_FAN_DIRECTION):
            value = self.dp_value(CONF_FAN_DIRECTION)
            if value is not None:
                if value == self._config.get(CONF_FAN_DIRECTION_FWD):
                    self._direction = DIRECTION_FORWARD

                if value == self._config.get(CONF_FAN_DIRECTION_REV):
                    self._direction = DIRECTION_REVERSE
            _LOGGER.debug("Fan current_direction : %s > %s", value, self._direction)


async_setup_entry = partial(async_setup_entry, DOMAIN, LocalTuyaFan, flow_schema)
