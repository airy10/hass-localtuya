"""Platform to locally control Tuya-based vacuum devices.

Core parity: ``LocalTuyaVacuum`` mirrors ``homeassistant/components/tuya/vacuum.py``
(``TuyaVacuumEntity``).

SYNC CHECKLIST (when the core component is updated):
  1. Diff ``homeassistant/components/tuya/vacuum.py`` against this file.
  2. Port: method bodies, ``__init__`` wrapper assignment, and
     ``_process_device_update``.
  3. Keep our deliberate deltas (they are intentional):
     - transport: reads/writes go over BLE/Ethernet via ``_read_wrapper`` /
       ``_async_send_wrapper_updates`` (``_async_send_commands`` sends
       ``{code, dp_id, value}``) instead of cloud MQTT.
     - construction: ``__init__(device, config_entry, dp_id, description=None)``
       resolves the fan-speed wrapper by dpcode via ``get_vacuum_definition``;
       the manual ``dps`` config (``dp_wrapper_by_id`` / ``RawDPWrapper``) is
       the fallback provider (SPEC_DEFINITION_DRIVEN_RUNTIME.md).
     - ``unique_id`` stays ``local_{device_id}_{dp_id}`` (avoids orphaning).
     - action DPs (power/stop/pause/locate) stay config-driven ``set_dp``; the
       activity classification state machine is localtuya-only.
"""

import logging
from functools import partial
from .config_flow import col_to_select

import voluptuous as vol
from homeassistant.components.vacuum import (
    DOMAIN,
    StateVacuumEntity,
    VacuumActivity,
    VacuumEntityFeature,
)

from .entity import LocalTuyaEntity, async_setup_entry
from .core.dp_wrappers import RawDPWrapper, dp_wrapper_by_id
from .core.definitions import get_vacuum_definition
from .const import (
    CONF_CLEAN_AREA_DP,
    CONF_CLEAN_RECORD_DP,
    CONF_CLEAN_TIME_DP,
    CONF_DOCKED_STATUS_VALUE,
    CONF_FAN_SPEED_DP,
    CONF_FAN_SPEEDS,
    CONF_FAULT_DP,
    CONF_IDLE_STATUS_VALUE,
    CONF_LOCATE_DP,
    CONF_MODE_DP,
    CONF_MODES,
    CONF_PAUSED_STATE,
    CONF_POWERGO_DP,
    CONF_RETURN_MODE,
    CONF_RETURNING_STATUS_VALUE,
    CONF_STOP_STATUS,
    CONF_PAUSE_DP,
)

_LOGGER = logging.getLogger(__name__)

CLEAN_TIME = "clean_time"
CLEAN_AREA = "clean_area"
CLEAN_RECORD = "clean_record"
MODES_LIST = "cleaning_mode_list"
MODE = "cleaning_mode"
FAULT = "fault"

DEFAULT_IDLE_STATUS = "standby,sleep"
DEFAULT_RETURNING_STATUS = "docking,to_charge,goto_charge"
DEFAULT_DOCKED_STATUS = "charging,chargecompleted,charge_done,charging_dock"
DEFAULT_MODES = "smart,wall_follow,spiral,single"
DEFAULT_FAN_SPEEDS = "low,normal,high"
DEFAULT_PAUSED_STATE = "paused"
DEFAULT_RETURN_MODE = "chargego"
DEFAULT_STOP_STATUS = "standby"


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Required(CONF_POWERGO_DP): col_to_select(dps, is_dps=True),
        vol.Required(CONF_IDLE_STATUS_VALUE, default=DEFAULT_IDLE_STATUS): str,
        vol.Required(CONF_DOCKED_STATUS_VALUE, default=DEFAULT_DOCKED_STATUS): str,
        vol.Optional(
            CONF_RETURNING_STATUS_VALUE, default=DEFAULT_RETURNING_STATUS
        ): str,
        vol.Optional(CONF_PAUSED_STATE, default=DEFAULT_PAUSED_STATE): str,
        vol.Optional(CONF_STOP_STATUS, default=DEFAULT_STOP_STATUS): str,
        vol.Optional(CONF_PAUSE_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_MODE_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_MODES, default=DEFAULT_MODES): str,
        vol.Optional(CONF_RETURN_MODE, default=DEFAULT_RETURN_MODE): str,
        vol.Optional(CONF_FAN_SPEED_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_FAN_SPEEDS, default=DEFAULT_FAN_SPEEDS): str,
        vol.Optional(CONF_CLEAN_TIME_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_CLEAN_AREA_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_CLEAN_RECORD_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_LOCATE_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_FAULT_DP): col_to_select(dps, is_dps=True),
    }


class LocalTuyaVacuum(LocalTuyaEntity, StateVacuumEntity):
    """Tuya vacuum device."""

    def __init__(self, device, config_entry, switchid, description=None, **kwargs):
        """Initialize a new LocalTuyaVacuum."""
        super().__init__(device, config_entry, switchid, _LOGGER, **kwargs)
        self._state = None
        self._attrs = {}

        self._idle_status_list = []
        if self.has_config(CONF_IDLE_STATUS_VALUE):
            status = self._config[CONF_IDLE_STATUS_VALUE].split(",")
            self._idle_status_list = [state.lstrip() for state in status]

        self._modes_list = []
        if self.has_config(CONF_MODES):
            modes_list = self._config[CONF_MODES].split(",")
            self._modes_list = [mode.lstrip() for mode in modes_list]
            self._attrs[MODES_LIST] = self._modes_list

        self._returning_status_list = []
        if self.has_config(CONF_RETURNING_STATUS_VALUE):
            returning_status = self._config[CONF_RETURNING_STATUS_VALUE].split(",")
            self._returning_status_list = [state.lstrip() for state in returning_status]

        self._docked_status_list = []
        if self.has_config(CONF_DOCKED_STATUS_VALUE):
            docked_status = self._config[CONF_DOCKED_STATUS_VALUE].split(",")
            self._docked_status_list = [state.lstrip() for state in docked_status]

        self._fan_speed_list = []
        if self.has_config(CONF_FAN_SPEEDS):
            fan_speeds = self._config[CONF_FAN_SPEEDS].split(",")
            self._fan_speed_list = [speed.lstrip() for speed in fan_speeds]

        self._cleaning_mode = ""

        # Core resolves action/fan_speed/activity wrappers; ours reads the
        # config status lists and writes config values, so only fan speed is
        # wrapper-delegated (enum options match the config list). DPs with no
        # cloud spec fall back to a raw wrapper.
        if description is not None:
            definition = get_vacuum_definition(device, description)
            self._fan_speed_wrapper = definition.fan_speed_wrapper
        else:
            self._fan_speed_wrapper = (
                dp_wrapper_by_id(device, self._config.get(CONF_FAN_SPEED_DP))
                or RawDPWrapper(self._config.get(CONF_FAN_SPEED_DP))
            ) if self.has_config(CONF_FAN_SPEED_DP) else None

    @property
    def supported_features(self) -> VacuumEntityFeature:
        """Flag supported features."""
        supported_features = (
            VacuumEntityFeature.START
            | VacuumEntityFeature.PAUSE
            | VacuumEntityFeature.STOP
            | VacuumEntityFeature.STATUS
            | VacuumEntityFeature.STATE
        )

        if (
            self.has_config(CONF_RETURN_MODE)
            and self._config[CONF_RETURN_MODE] in self._modes_list
        ):
            supported_features |= VacuumEntityFeature.RETURN_HOME
        if self.has_config(CONF_FAN_SPEED_DP):
            supported_features |= VacuumEntityFeature.FAN_SPEED
        if self.has_config(CONF_LOCATE_DP):
            supported_features |= VacuumEntityFeature.LOCATE

        return supported_features

    @property
    def fan_speed(self):
        """Return the fan speed of the vacuum cleaner."""
        return self._read_wrapper(self._fan_speed_wrapper)

    @property
    def fan_speed_list(self) -> list:
        """Return the list of available fan speeds."""
        return self._fan_speed_list

    @property
    def activity(self) -> VacuumActivity | None:
        """Return Tuya vacuum device state."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return the specific state attributes of this vacuum cleaner."""
        return self._attrs

    async def async_start(self, **kwargs):
        """Start the device."""
        await self._device.set_dp(True, self._config[CONF_POWERGO_DP])

    async def async_stop(self, **kwargs):
        """Stop the device."""
        if (
            self.has_config(CONF_STOP_STATUS)
            and self._config[CONF_STOP_STATUS] in self._modes_list
        ):
            await self._device.set_dp(
                self._config[CONF_STOP_STATUS], self._config[CONF_MODE_DP]
            )
        else:
            await self._device.set_dp(False, self._config[CONF_POWERGO_DP])
            # _LOGGER.error("Missing command for stop in commands set.")

    async def async_pause(self, **kwargs):
        """Pause the device."""
        if self.has_config(CONF_PAUSE_DP):
            return await self._device.set_dp(True, self._config[CONF_PAUSE_DP])

        await self.async_stop()

    async def async_return_to_base(self, **kwargs):
        """Return device to dock."""
        if self.has_config(CONF_RETURN_MODE):
            await self._device.set_dp(
                self._config[CONF_RETURN_MODE], self._config[CONF_MODE_DP]
            )
        else:
            _LOGGER.error("Missing command for return home in commands set.")

    async def async_clean_spot(self, **kwargs):
        """Perform a spot clean-up."""
        return None

    async def async_locate(self, **kwargs):
        """Locate the device."""
        if self.has_config(CONF_LOCATE_DP):
            await self._device.set_dp(True, self._config[CONF_LOCATE_DP])

    async def async_set_fan_speed(self, fan_speed, **kwargs):
        """Set fan speed."""
        await self._async_send_wrapper_updates(self._fan_speed_wrapper, fan_speed)

    async def async_send_command(self, command, params=None, **kwargs):
        """Send raw command."""
        if command == "set_mode" and "mode" in params:
            mode = params["mode"]
            await self._device.set_dp(mode, self._config[CONF_MODE_DP])

    def status_updated(self):
        """Device status was updated."""
        state_value = self.dp_value(self._dp_id)

        if state_value is None:
            self._state = None
        elif state_value in self._idle_status_list:
            self._state = VacuumActivity.IDLE
        elif state_value in self._docked_status_list:
            self._state = VacuumActivity.DOCKED
        elif state_value in self._returning_status_list:
            self._state = VacuumActivity.RETURNING
        elif state_value in [self._config[CONF_PAUSED_STATE], "pause"] or (
            self.dp_value(CONF_PAUSE_DP) is True
        ):
            self._state = VacuumActivity.PAUSED
        else:
            self._state = VacuumActivity.CLEANING

        self._cleaning_mode = ""
        if self.has_config(CONF_MODES):
            self._cleaning_mode = self.dp_value(CONF_MODE_DP)
            self._attrs[MODE] = self._cleaning_mode

        if self.has_config(CONF_CLEAN_TIME_DP):
            self._attrs[CLEAN_TIME] = self.dp_value(CONF_CLEAN_TIME_DP)

        if self.has_config(CONF_CLEAN_AREA_DP):
            self._attrs[CLEAN_AREA] = self.dp_value(CONF_CLEAN_AREA_DP)

        if self.has_config(CONF_CLEAN_RECORD_DP):
            self._attrs[CLEAN_RECORD] = self.dp_value(CONF_CLEAN_RECORD_DP)

        if self.has_config(CONF_FAULT_DP):
            self._attrs[FAULT] = self.dp_value(CONF_FAULT_DP)
            if self._attrs[FAULT] != 0:
                self._state = VacuumActivity.ERROR


async_setup_entry = partial(async_setup_entry, DOMAIN, LocalTuyaVacuum, flow_schema)
