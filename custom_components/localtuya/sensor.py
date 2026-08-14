"""Platform to present any Tuya DP as a sensor."""

import logging
import base64
from functools import partial
from .config_flow import col_to_select

import voluptuous as vol
from homeassistant.components.sensor import (
    DEVICE_CLASSES_SCHEMA,
    DOMAIN,
    STATE_CLASSES_SCHEMA,
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    CONF_DEVICE_CLASS,
    CONF_DEVICES,
    CONF_ENTITIES,
    CONF_ENTITY_CATEGORY,
    CONF_FRIENDLY_NAME,
    CONF_ID,
    CONF_PLATFORM,
    CONF_UNIT_OF_MEASUREMENT,
    Platform,
    STATE_UNKNOWN,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfPower,
)
from homeassistant.helpers import entity_registry as er

from .core.dp_wrappers import DPCodeEnumWrapper, RawDPWrapper, dp_wrapper_by_id
from .core.definitions import get_sensor_definition
from .entity import LocalTuyaEntity, async_setup_entry as _setup_entry
from .const import (
    CONF_ENTITY_ENABLED_DEFAULT,
    CONF_ICONS,
    CONF_NODE_ID,
    CONF_SCALING,
    CONF_OFFSET,
    CONF_STATE_CLASS,
    DOMAIN as LOCALTUYA_DOMAIN,
    TRANSPORT_BLE,
    get_device_key,
)

_LOGGER = logging.getLogger(__name__)

DEFAULT_PRECISION = 2

ATTR_POWER = "power"
ATTR_VOLTAGE = "voltage"
ATTR_CURRENT = "current"
MAP_UOM = {
    ATTR_CURRENT: UnitOfElectricCurrent.AMPERE,
    ATTR_VOLTAGE: UnitOfElectricPotential.VOLT,
    ATTR_POWER: UnitOfPower.KILO_WATT,
}


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(CONF_UNIT_OF_MEASUREMENT): str,
        vol.Optional(CONF_DEVICE_CLASS): DEVICE_CLASSES_SCHEMA,
        vol.Optional(CONF_STATE_CLASS): col_to_select(
            [sc.value for sc in SensorStateClass]
        ),
        vol.Optional(CONF_SCALING): vol.All(
            vol.Coerce(float), vol.Range(min=-1000000.0, max=1000000.0)
        ),
        vol.Optional(CONF_OFFSET): vol.All(
            vol.Coerce(float), vol.Range(min=-1000000.0, max=1000000.0)
        ),
        vol.Optional(CONF_ICONS): [str],
        vol.Optional(CONF_ENTITY_ENABLED_DEFAULT, default=True): bool,
    }


class LocalTuyaSensor(LocalTuyaEntity, SensorEntity):
    """Representation of a Tuya sensor."""

    def __init__(
        self,
        device,
        config_entry,
        sensorid,
        description=None,
        **kwargs,
    ):
        """Initialize the Tuya sensor."""
        super().__init__(device, config_entry, sensorid, _LOGGER, **kwargs)
        self._state = None

        self._has_sub_entities = False
        self._attr_device_class = self._config.get(CONF_DEVICE_CLASS)

        # Definition-driven: resolve the primary DP by dpcode; the manual
        # config-driven dps path is the fallback.
        if description is not None:
            definition = get_sensor_definition(device, description)
            self._dpcode_wrapper = (
                definition.dpcode_wrapper if definition is not None else None
            )
        else:
            # Cloud spec (core sensor_wrapper) as default source for unit/class.
            self._dpcode_wrapper = dp_wrapper_by_id(
                device, self._dp_id
            ) or RawDPWrapper(self._dp_id)
        if not self.has_config(CONF_UNIT_OF_MEASUREMENT) and (
            unit := self._dpcode_wrapper.native_unit
            or self._dpcode_wrapper.suggested_unit
        ):
            self._attr_native_unit_of_measurement = unit
        # For enum DPs, we can assume it's an ENUM sensor (core parity)
        if (
            self._attr_device_class is None
            and isinstance(self._dpcode_wrapper, DPCodeEnumWrapper)
        ):
            self._attr_device_class = SensorDeviceClass.ENUM
            self._attr_options = self._dpcode_wrapper.options

    @property
    def native_value(self):
        """Return the value reported by the sensor."""
        if (
            not self.has_config(CONF_SCALING)
            and not self.has_config(CONF_OFFSET)
            and not self.is_base64(self.dp_value(self._dp_id))
        ):
            return self._read_wrapper(self._dpcode_wrapper)
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
    def state_class(self) -> str | None:
        """Return state class."""
        return getattr(self, "_attr_state_class", self._config.get(CONF_STATE_CLASS))

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return getattr(
            self,
            "_attr_native_unit_of_measurement",
            self._config.get(CONF_UNIT_OF_MEASUREMENT),
        )

    def status_updated(self):
        """Device status was updated."""

        state = self.dp_value(self._dp_id)

        if self.is_base64(state):
            if not self._has_sub_entities:
                self.hass.loop.call_soon_threadsafe(
                    self.hass.async_create_task, self.__create_sub_sensors()
                )

            if None not in (
                sub_sensor := getattr(self, "_attr_sub_sensor", None),
                sub_sensor_state := self.decode_base64(state).get(sub_sensor),
            ):
                self._state = sub_sensor_state
            else:
                self._state = state
        else:
            self._state = self.scale(state)

        icons = self._config.get(CONF_ICONS)
        if icons and isinstance(self._state, int) and 0 <= self._state < len(icons):
            self._attr_icon = icons[self._state]
        else:
            self._attr_icon = None

    def status_restored(self, stored_state) -> None:
        super().status_restored(stored_state)

        if (last_state := self._last_state) and self.is_base64(last_state):
            self._status.update({self._dp_id: last_state})

    # No need to restore state for a sensor
    async def restore_state_when_connected(self):
        """Do nothing for a sensor."""
        return

    def is_base64(self, data):
        """Return if the data is valid Tuya raw Base64 encoded data."""
        return (
            (data and isinstance(data, str))
            and len(data) >= 12
            and len(data) % 2 == 0
            and data.endswith("=")
        )

    def decode_base64(self, data):
        """Decode data base64 such as DPS phase_a."""
        buf = base64.b64decode(data)
        voltage = (buf[1] | buf[0] << 8) / 10
        current = (buf[4] | buf[3] << 8) / 1000
        power = (buf[7] | buf[6] << 8) / 1000
        return {ATTR_VOLTAGE: voltage, ATTR_CURRENT: current, ATTR_POWER: power}

    async def __create_sub_sensors(self):
        """Create sub entities for voltage, current and power and hide this parent sensor."""
        sub_entities = []

        for sensor in (ATTR_CURRENT, ATTR_POWER, ATTR_VOLTAGE):
            sub_entity = LocalTuyaSensor(
                self._device, self._device_config.as_dict(), self._dp_id
            )
            setattr(sub_entity, "_attr_sub_sensor", sensor)
            setattr(sub_entity, "_attr_unique_id", f"{self.unique_id}_{sensor}")
            setattr(sub_entity, "_attr_name", f"{self.name} {sensor.capitalize()}")
            setattr(sub_entity, "_attr_device_class", SensorDeviceClass(sensor))
            setattr(sub_entity, "_attr_state_class", SensorStateClass.MEASUREMENT)
            setattr(sub_entity, "_attr_native_unit_of_measurement", MAP_UOM[sensor])
            sub_entities.append(sub_entity)

        # Sub entities shouldn't have add entities attr.
        if sub_entities and self.componet_add_entities:
            self._has_sub_entities = True
            self.componet_add_entities(sub_entities)
            er.async_get(self.hass).async_update_entity(
                self.entity_id, hidden_by=er.RegistryEntryHider.INTEGRATION
            )


class LocalTuyaRSSISensor(LocalTuyaSensor):
    """Diagnostic sensor exposing the BLE signal strength."""

    def __init__(self, device, device_config):
        """Initialize the RSSI sensor."""
        rssi_config = {
            CONF_ID: "rssi",
            CONF_PLATFORM: DOMAIN,
            CONF_FRIENDLY_NAME: "Signal Strength",
            CONF_DEVICE_CLASS: SensorDeviceClass.SIGNAL_STRENGTH,
            CONF_ENTITY_CATEGORY: "diagnostic",
            CONF_ENTITY_ENABLED_DEFAULT: False,
        }
        synthetic = {**device_config, CONF_ENTITIES: [rssi_config]}
        super().__init__(device, synthetic, "rssi")
        self._attr_native_unit_of_measurement = "dBm"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        """Return the signal strength."""
        return self._device.rssi


_setup_entry = partial(_setup_entry, DOMAIN, LocalTuyaSensor, flow_schema)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Tuya sensors, adding a BLE RSSI diagnostic sensor."""
    await _setup_entry(hass, config_entry, async_add_entities)

    hass_entry_data = hass.data[LOCALTUYA_DOMAIN][config_entry.entry_id]
    for dev_id in config_entry.data[CONF_DEVICES]:
        dev_entry = config_entry.data[CONF_DEVICES][dev_id]
        host = get_device_key(dev_entry)
        node_id = dev_entry.get(CONF_NODE_ID)
        device_key = f"{host}_{node_id}" if node_id else host
        if device_key not in hass_entry_data.devices:
            continue
        device = hass_entry_data.devices[device_key]
        if device._device_config.transport != TRANSPORT_BLE:
            continue
        rssi_entities = [LocalTuyaRSSISensor(device, dev_entry)]
        device.add_entities(rssi_entities)
        async_add_entities(rssi_entities)
