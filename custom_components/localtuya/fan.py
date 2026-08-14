"""Platform to locally control Tuya-based fan devices.

Core parity: ``LocalTuyaFan`` mirrors ``homeassistant/components/tuya/fan.py``
(``TuyaFanEntity``).

SYNC CHECKLIST (when the core component is updated):
  1. Diff ``homeassistant/components/tuya/fan.py`` against this file.
  2. Port: method bodies, ``__init__`` wrapper assignment, and
     ``_process_device_update``.
  3. Keep our deliberate deltas (they are intentional):
     - transport: reads/writes go over BLE/Ethernet via ``_read_wrapper`` /
       ``_async_send_wrapper_updates`` (``_async_send_commands`` sends
       ``{code, dp_id, value}``) instead of cloud MQTT.
     - construction: ``__init__(device, config_entry, dp_id, description=None)``
       resolves wrappers by dpcode via ``get_fan_definition``; the manual
       ``dps`` config (``dp_wrapper_by_id`` / ``RawDPWrapper``) is the fallback
       provider (SPEC_DEFINITION_DRIVEN_RUNTIME.md).
     - ``unique_id`` stays ``local_{device_id}_{dp_id}`` (avoids orphaning).
     - percentage↔speed scaling, fwd/rev direction mapping, and
       ``speed_count`` / ordered-speed-list handling stay config-driven.
"""

import logging
from functools import partial
from typing import Any, override

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
from .core.definitions import get_fan_definition
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
        description=None,
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

        if description is not None:
            # Definition-driven: resolve the DP wrappers by dpcode.
            definition = get_fan_definition(device, description)
            self._switch_wrapper = (
                definition.switch_wrapper if definition is not None else None
            )
            speed_inner = (
                definition.speed_wrapper if definition is not None else None
            )
            osc_inner = (
                definition.oscillate_wrapper if definition is not None else None
            )
            dir_inner = (
                definition.direction_wrapper if definition is not None else None
            )
            mode_inner = (
                definition.mode_wrapper if definition is not None else None
            )
        else:
            # Manual config-driven path: cloud spec wrappers fall back to a
            # raw wrapper. Speed/direction conversion lives in the decorators.
            self._switch_wrapper = dp_wrapper_by_id(
                device, self._dp_id
            ) or RawDPWrapper(self._dp_id)

            speed_dp = self._config.get(CONF_FAN_SPEED_CONTROL)
            speed_inner = (
                dp_wrapper_by_id(device, speed_dp) or RawDPWrapper(speed_dp)
            ) if self.has_config(CONF_FAN_SPEED_CONTROL) else None

            osc_dp = self._config.get(CONF_FAN_OSCILLATING_CONTROL)
            osc_inner = (
                dp_wrapper_by_id(device, osc_dp) or RawDPWrapper(osc_dp)
            ) if self.has_config(CONF_FAN_OSCILLATING_CONTROL) else None

            dir_dp = self._config.get(CONF_FAN_DIRECTION)
            dir_inner = (
                dp_wrapper_by_id(device, dir_dp) or RawDPWrapper(dir_dp)
            ) if self.has_config(CONF_FAN_DIRECTION) else None

            # No manual fan_mode flow option; preset modes are only available
            # through the definition-driven (cloud) path.
            mode_inner = None

        self._speed_wrapper = (
            FanSpeedPercentageWrapper(
                speed_inner,
                self._speed_range,
                self._ordered_list if self._use_ordered_list else None,
            )
            if speed_inner is not None
            else None
        )
        self._oscillate_wrapper = osc_inner
        self._direction_wrapper = (
            FanDirectionWrapper(
                dir_inner,
                self._config.get(CONF_FAN_DIRECTION_FWD),
                self._config.get(CONF_FAN_DIRECTION_REV),
            )
            if dir_inner is not None
            else None
        )
        self._mode_wrapper = mode_inner
        self._attr_preset_modes = (
            self._mode_wrapper.options if self._mode_wrapper is not None else None
        )

    @override
    async def async_set_direction(self, direction: str) -> None:
        """Set the direction of the fan."""
        await self._async_send_wrapper_updates(self._direction_wrapper, direction)
        self.schedule_update_ha_state()

    @override
    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed of the fan, as a percentage."""
        if percentage is not None:
            if percentage == 0:
                return await self.async_turn_off()
            if not self.is_on:
                await self.async_turn_on()
            await self._async_send_wrapper_updates(self._speed_wrapper, percentage)
            self.schedule_update_ha_state()

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the fan off."""
        await self._async_send_wrapper_updates(self._switch_wrapper, False)
        self.schedule_update_ha_state()

    @override
    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode of the fan."""
        await self._async_send_wrapper_updates(self._mode_wrapper, preset_mode)
        self.schedule_update_ha_state()

    @override
    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan."""
        if self._switch_wrapper is None:
            return

        commands = self._switch_wrapper.get_update_commands(self._device, True)

        if percentage is not None and self._speed_wrapper is not None:
            commands.extend(
                self._speed_wrapper.get_update_commands(self._device, percentage)
            )

        if preset_mode is not None and self._mode_wrapper is not None:
            commands.extend(
                self._mode_wrapper.get_update_commands(self._device, preset_mode)
            )
        await self._async_send_commands(commands)
        self.schedule_update_ha_state()

    @override
    async def async_oscillate(self, oscillating: bool) -> None:
        """Oscillate the fan."""
        await self._async_send_wrapper_updates(self._oscillate_wrapper, oscillating)
        self.schedule_update_ha_state()

    @property
    @override
    def is_on(self) -> bool | None:
        """Return true if fan is on."""
        return self._read_wrapper(self._switch_wrapper)

    @property
    @override
    def current_direction(self) -> str | None:
        """Return the current direction of the fan."""
        return self._read_wrapper(self._direction_wrapper)

    @property
    @override
    def oscillating(self) -> bool | None:
        """Return true if the fan is oscillating."""
        return self._read_wrapper(self._oscillate_wrapper)

    @property
    @override
    def percentage(self) -> int | None:
        """Return the current speed."""
        return self._read_wrapper(self._speed_wrapper)

    @property
    @override
    def preset_mode(self) -> str | None:
        """Return the current preset_mode."""
        return self._read_wrapper(self._mode_wrapper)

    @property
    @override
    def supported_features(self) -> FanEntityFeature:
        """Flag supported features."""
        features = FanEntityFeature(0)

        if self._oscillate_wrapper is not None:
            features |= FanEntityFeature.OSCILLATE

        if self._speed_wrapper is not None:
            features |= FanEntityFeature.SET_SPEED

        if self._direction_wrapper is not None:
            features |= FanEntityFeature.DIRECTION

        if self._mode_wrapper is not None:
            features |= FanEntityFeature.PRESET_MODE

        features |= FanEntityFeature.TURN_OFF
        features |= FanEntityFeature.TURN_ON

        return features

    @property
    @override
    def speed_count(self) -> int:
        """Speed count for the fan."""
        if self._use_ordered_list:
            return len(self._ordered_list)
        return int_states_in_range(self._speed_range)


async_setup_entry = partial(async_setup_entry, DOMAIN, LocalTuyaFan, flow_schema)
