"""
    Tuya Devices: https://xzetsubou.github.io/hass-localtuya/auto_configure/

    This functionality is similar to HA Tuya, as it retrieves the category and searches for the corresponding categories. 
    The categories data has been improved & modified to work seamlessly with localtuya

    Device Data: You can obtain all the data for your device from Home Assistant by directly downloading the diagnostics or using entry diagnostics.
        Alternative: Use Tuya IoT.

    Add a new device or modify an existing one:
        1. Make sure the device category doesn't already exist. If you are creating a new one, you can modify existing categories.
        2. In order to add a device, you need to specify the category of the device you want to add inside the entity type dictionary.
    
    Add entities to devices:
        1. Open the file with the name of the entity type on which you want to make changes [e.g. switches.py] and search for your device category.
        2. You can add entities inside the tuple value of the dictionary by including LocalTuyaEntity and passing the parameters for the entity configurations.
        3. These configurations include "id" (required), "icon" (optional), "device_class" (optional), "state_class" (optional), and "name" (optional) [Using COVERS as an example]
            Example: "3 ( code: percent_state , value: 0 )" - Refer to the Device Data section above for more details.
                current_state_dp = DPCode.PERCENT_STATE < This maps the "percent_state" code DP to the current_state_dp configuration.

            If the configuration is not DPS, it will be inserted through "custom_configs". This is used to inject any configuration into the entity configuration
                Example: custom_configs={"positioning_mode": "position"}. I hope that clarifies the concept
                
        Check URL above for more details. 
"""

from homeassistant.const import Platform

# Supported files
from .alarm_control_panels import ALARMS  # not added yet
from .binary_sensors import BINARY_SENSORS
from .buttons import BUTTONS
from .climates import CLIMATES
from .covers import COVERS
from .events import EVENTS
from .fans import FANS
from .humidifiers import HUMIDIFIERS
from .lights import LIGHTS
from .numbers import NUMBERS
from .remotes import REMOTES
from .selects import SELECTS
from .sensors import SENSORS
from .sirens import SIRENS
from .switches import SWITCHES
from .texts import TEXTS
from .vacuums import VACUUMS
from .valves import VALVES
from .locks import LOCKS
from .water_heaters import WATER_HEATERS

# The supported PLATFORMS [ Platform: Data ]
DATA_PLATFORMS = {
    Platform.ALARM_CONTROL_PANEL: ALARMS,
    Platform.BINARY_SENSOR: BINARY_SENSORS,
    Platform.BUTTON: BUTTONS,
    Platform.CLIMATE: CLIMATES,
    Platform.COVER: COVERS,
    Platform.EVENT: EVENTS,
    Platform.FAN: FANS,
    Platform.HUMIDIFIER: HUMIDIFIERS,
    Platform.LIGHT: LIGHTS,
    Platform.LOCK: LOCKS,
    Platform.NUMBER: NUMBERS,
    Platform.REMOTE: REMOTES,
    Platform.SELECT: SELECTS,
    Platform.SENSOR: SENSORS,
    Platform.SIREN: SIRENS,
    Platform.SWITCH: SWITCHES,
    Platform.TEXT: TEXTS,
    Platform.VACUUM: VACUUMS,
    Platform.VALVE: VALVES,
    Platform.WATER_HEATER: WATER_HEATERS,
}


def category_has_descriptions(category: str) -> bool:
    """Return True when any platform table declares entities for a category.

    Used by the config flow to decide whether a device's cloud category can be
    auto-configured from the ``ha_entities`` tables (definition-driven runtime)
    without flattening to a ``dps`` config.
    """
    return any(bool(table.get(category)) for table in DATA_PLATFORMS.values())
