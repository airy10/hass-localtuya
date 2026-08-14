"""Platform to locally control Tuya-based light devices."""

import logging
import voluptuous as vol

from dataclasses import dataclass
from functools import partial
from homeassistant.helpers import selector
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_EFFECT,
    ATTR_HS_COLOR,
    ATTR_WHITE,
    ColorMode,
    DOMAIN,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.const import CONF_BRIGHTNESS, CONF_COLOR_TEMP, CONF_SCENE

from .config_flow import col_to_select
from .entity import LocalTuyaEntity, async_setup_entry
from .core.dp_wrappers import RawDPWrapper, dp_wrapper_by_id
from .core.dp_wrapper_decorators import (
    BrightnessWrapper,
    ColorTempWrapper,
    ColorTypeData,
    StringColorWrapper,
    map_range,
)
from .const import (
    CONF_BRIGHTNESS_LOWER,
    CONF_BRIGHTNESS_UPPER,
    CONF_COLOR,
    CONF_COLOR_MODE,
    CONF_COLOR_MODE_SET,
    CONF_COLOR_TEMP_MAX_KELVIN,
    CONF_COLOR_TEMP_MIN_KELVIN,
    CONF_COLOR_TEMP_REVERSE,
    CONF_COLOR_TYPE_DATA,
    CONF_MUSIC_MODE,
    CONF_SCENE_VALUES,
    DictSelector,
)

_LOGGER = logging.getLogger(__name__)

DEFAULT_MIN_KELVIN = 2700  # MIRED 370
DEFAULT_MAX_KELVIN = 6500  # MIRED 153

DEFAULT_COLOR_TEMP_REVERSE = False

DEFAULT_LOWER_BRIGHTNESS = 10
DEFAULT_UPPER_BRIGHTNESS = 1000

MODE_MANUAL = "manual"
MODE_COLOR = "colour"
MODE_MUSIC = "music"
MODE_SCENE = "scene"
MODE_WHITE = "white"
# Fallback music work_mode values when no cloud spec is available.
MODE_MUSIC_ALIASES = ("dynamic_mod",)

SCENE_MUSIC = "Music"

MODES_SET = {"Colour, Music, Scene and White": 0, "Manual, Music, Scene and White": 1}

# https://developer.tuya.com/en/docs/iot/dj?id=K9i5ql3v98hn3#title-10-scene_data
SCENE_LIST_RGBW_255 = {
    "Night": "bd76000168ffff",
    "Read": "fffcf70168ffff",
    "Meeting": "cf38000168ffff",
    "Leisure": "3855b40168ffff",
    "Scenario 1": "scene_1",
    "Scenario 2": "scene_2",
    "Scenario 3": "scene_3",
    "Scenario 4": "scene_4",
}

# https://developer.tuya.com/en/docs/iot/dj?id=K9i5ql3v98hn3#title-11-scene_data_v2
SCENE_LIST_RGBW_1000 = {
    "Night 1": "000e0d0000000000000000c80000",
    "Night 2": "000e0d00002e03e802cc00000000",
    "Read 1": "010e0d0000000000000003e801f4",
    "Read 2": "010e0d000084000003e800000000",
    "Meeting": "020e0d0000000000000003e803e8",
    "Working": "020e0d00001403e803e800000000",
    "Leisure 1": "030e0d0000000000000001f401f4",
    "Leisure 2": "030e0d0000e80383031c00000000",
    "Soft": "04464602007803e803e800000000464602007803e8000a00000000",
    "Rainbow": "05464601000003e803e800000000464601007803e803e80000000046460100f003e803"
    + "e800000000",
    "Colorful": "06464601000003e803e800000000464601007803e803e80000000046460100f003e80"
    + "3e800000000464601003d03e803e80000000046460100ae03e803e800000000464601011303e803"
    + "e800000000",
    "Beautiful": "07464602000003e803e800000000464602007803e803e80000000046460200f003e8"
    + "03e800000000464602003d03e803e80000000046460200ae03e803e800000000464602011303e80"
    + "3e800000000",
    "Forest": "19464601007803e803e800000000464602006e0320025800000000464602005a038403e8"
    + "00000000",
    "Dream": "1c4646020104032003e800000000464602011802bc03e800000000464602011303e803e80"
    + "0000000",
    "F Style": "1e323201015e01f403e800000000323202003201f403e80000000032320200a001f403e"
    + "800000000",
    "A Style": "1f46460100dc02bc03e800000000464602006e03200258000000004646020014038403e"
    + "800000000464601012703e802ee0000000046460100000384028a00000000",
    "Halloween": "28464601011303e803e800000000464601001e03e803e800000000",
    "Christmas": "225a5a0100f003e803e8000000005a5a01003d03e803e800000000464601000003e80"
    + "3e8000000005a5a0100ae03e803e8000000005a5a01011303e803e800000000464601007803e803e"
    + "800000000",
    "Birthday": "20646401003d03e803e800000000646401007803e803e8000000005a5a01011303e803"
    + "e8000000005a5a0100ae03e803e800000000646401003201f403e800000000646401000003e803e8"
    + "00000000",
    "Wedding Anniversary": "21323202015e01f403e800000000323202011303e803e800000000",
}

# Same format as SCENE_LIST_RGBW_1000
SCENE_LIST_RGB_1000 = {
    "Night": "000e0d00002e03e802cc00000000",
    "Read": "010e0d000084000003e800000000",
    "Working": "020e0d00001403e803e800000000",
    "Leisure": "030e0d0000e80383031c00000000",
    "Soft": "04464602007803e803e800000000464602007803e8000a00000000",
    "Colorful": "05464601000003e803e800000000464601007803e803e80000000046460100f003e80"
    + "3e800000000464601003d03e803e80000000046460100ae03e803e800000000464601011303e803"
    + "e800000000",
    "Dazzling": "06464601000003e803e800000000464601007803e803e80000000046460100f003e80"
    + "3e800000000",
    "Gorgeous": "07464602000003e803e800000000464602007803e803e80000000046460200f003e803e8"
    + "00000000464602003d03e803e80000000046460200ae03e803e800000000464602011303e803e80"
    + "0000000",
}

SCENE_LIST_RGBW_BLE = {
    "Good Night": "AAAAAGQKQA==",
    "Reading": "AQAAAGRkCA==",
    "Work": "AgAAAGRkAQ==",
    "Leisure": "AwAAAGQ8BA==",
    "White Breath": "BgACADxkAYA=",
    "White Flashing": "BwABADJkAYA=",
    "Warm Breath": "BwABADJkAYA=",
    "Warm Flashing": "CQABADJkQIA=",
    "Rainbow": "CgACAUtkAQIEECAI",
    "Blue & Green Gradient": "CwACAUtkAgQ=",
    "Red & Green Gradient": "DAACAUtkAQQ=",
    "Red & Blue Gradient": "DQACAUtkAQI=",
    "Red & Blue & Green Gradient": "DgACATxkAYACgASA",
    "Red Breath": "DwACATxkAYA=",
    "Flash": "FAABATJkAQIEECAI",
}


@dataclass(frozen=True)
class Mode:
    color: str = MODE_COLOR
    music: str = MODE_MUSIC
    scene: str = MODE_SCENE
    white: str = MODE_WHITE

    def as_list(self) -> list:
        return [self.color, self.music, self.scene, self.white]

    def as_dict(self) -> dict[str, str]:
        default = {"Default": self.white}
        return {**default, "Mode Color": self.color, "Mode Scene": self.scene}


MAP_MODE_SET = {0: Mode(), 1: Mode(color=MODE_MANUAL)}


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(CONF_BRIGHTNESS): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_COLOR_TEMP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_BRIGHTNESS_LOWER, default=DEFAULT_LOWER_BRIGHTNESS): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=10000)
        ),
        vol.Optional(CONF_BRIGHTNESS_UPPER, default=DEFAULT_UPPER_BRIGHTNESS): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=10000)
        ),
        vol.Optional(CONF_COLOR_MODE): col_to_select(dps, is_dps=True),
        vol.Required(CONF_COLOR_MODE_SET, default="0"): col_to_select(MODES_SET),
        vol.Optional(CONF_COLOR): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_COLOR_TEMP_MIN_KELVIN, default=DEFAULT_MIN_KELVIN): vol.All(
            vol.Coerce(int), vol.Range(min=1500, max=8000)
        ),
        vol.Optional(CONF_COLOR_TEMP_MAX_KELVIN, default=DEFAULT_MAX_KELVIN): vol.All(
            vol.Coerce(int), vol.Range(min=1500, max=8000)
        ),
        vol.Optional(CONF_COLOR_TEMP_REVERSE, default=DEFAULT_COLOR_TEMP_REVERSE): bool,
        vol.Optional(CONF_COLOR_TYPE_DATA): selector.ObjectSelector(),
        vol.Optional(CONF_SCENE): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_SCENE_VALUES, default={}): selector.ObjectSelector(),
        vol.Optional(CONF_MUSIC_MODE, default=False): selector.BooleanSelector(),
    }


class LocalTuyaLight(LocalTuyaEntity, LightEntity):
    """Representation of a Tuya light."""

    def __init__(
        self,
        device,
        config_entry,
        lightid,
        **kwargs,
    ):
        """Initialize the Tuya light."""
        super().__init__(device, config_entry, lightid, _LOGGER, **kwargs)
        # Light is an active device (mains powered). It should be able
        # to respond at any time. But Tuya BLE bulbs are write-only.
        self._write_only = self._device.is_write_only

        self._state = None
        self._lower_brightness = int(
            self._config.get(CONF_BRIGHTNESS_LOWER, DEFAULT_LOWER_BRIGHTNESS)
        )
        self._upper_brightness = int(
            self._config.get(CONF_BRIGHTNESS_UPPER, DEFAULT_UPPER_BRIGHTNESS)
        )
        self._upper_color_temp = self._upper_brightness

        self._color_type_data = ColorTypeData.from_config(
            self._config.get(CONF_COLOR_TYPE_DATA)
        )
        self._modes = MAP_MODE_SET[int(self._config.get(CONF_COLOR_MODE_SET, 0))]
        self._work_mode_range: list[str] | None = None
        self._effect_list = []
        self._scenes = DictSelector({})
        self._cached_status = {}

        # Cloud spec wrappers for the configured DPs (core parity); DPs with
        # no cloud spec fall back to a raw wrapper so reads/writes always
        # delegate through the wrapper layer. Color/brightness/color_temp
        # conversion lives in the decorators.
        self._switch_wrapper = dp_wrapper_by_id(
            device, self._dp_id
        ) or RawDPWrapper(self._dp_id)

        brightness_dp = self._config.get(CONF_BRIGHTNESS)
        if self.has_config(CONF_BRIGHTNESS):
            inner = dp_wrapper_by_id(device, brightness_dp) or RawDPWrapper(
                brightness_dp
            )
            self._brightness_wrapper = BrightnessWrapper(
                inner, self._lower_brightness, self._upper_brightness
            )
        else:
            self._brightness_wrapper = None

        min_kelvin = int(
            self._config.get(CONF_COLOR_TEMP_MIN_KELVIN, DEFAULT_MIN_KELVIN)
        )
        max_kelvin = int(
            self._config.get(CONF_COLOR_TEMP_MAX_KELVIN, DEFAULT_MAX_KELVIN)
        )
        color_temp_dp = self._config.get(CONF_COLOR_TEMP)
        if self.has_config(CONF_COLOR_TEMP):
            inner = dp_wrapper_by_id(device, color_temp_dp) or RawDPWrapper(
                color_temp_dp
            )
            self._color_temp_wrapper = ColorTempWrapper(
                inner,
                min_kelvin,
                max_kelvin,
                self._lower_brightness,
                self._upper_brightness,
                self._config.get(CONF_COLOR_TEMP_REVERSE, DEFAULT_COLOR_TEMP_REVERSE),
            )
        else:
            self._color_temp_wrapper = None

        # Work mode is read/written as a raw string (config-driven string
        # comparison), so it always resolves to a raw wrapper by dp_id.
        color_mode_dp = self._config.get(CONF_COLOR_MODE)
        self._color_mode_wrapper = (
            RawDPWrapper(color_mode_dp)
        ) if self.has_config(CONF_COLOR_MODE) else None

        scene_dp = self._config.get(CONF_SCENE)
        self._scene_wrapper = (
            dp_wrapper_by_id(device, scene_dp) or RawDPWrapper(scene_dp)
        ) if self.has_config(CONF_SCENE) else None

        color_dp = self._config.get(CONF_COLOR)
        if self.has_config(CONF_COLOR):
            inner = dp_wrapper_by_id(device, color_dp) or RawDPWrapper(color_dp)
            self._color_data_wrapper = StringColorWrapper(
                inner, self._color_type_data, self._upper_brightness
            )
        else:
            self._color_data_wrapper = None

        if self._config.get(CONF_MUSIC_MODE):
            self._effect_list.append(SCENE_MUSIC)

        self._attr_min_color_temp_kelvin = min_kelvin
        self._attr_max_color_temp_kelvin = max_kelvin

    def connection_made(self):
        """The connection has made with the device and status retrieved, Configure the entity based on its reserved status."""
        super().connection_made()
        is_write_only = self._write_only

        if self.has_config(CONF_SCENE):
            if (cf_scenes := self._config.get(CONF_SCENE_VALUES)) and len(cf_scenes):
                scenes = {v: k for k, v in cf_scenes.items()}
            else:
                scene_value = self.dp_value(CONF_SCENE)
                if is_write_only and not scene_value:
                    scenes = SCENE_LIST_RGBW_BLE
                elif scene_value and len(scene_value) <= 20:
                    scenes = SCENE_LIST_RGBW_255
                elif self._config.get(CONF_BRIGHTNESS) is None:
                    scenes = SCENE_LIST_RGB_1000
                else:
                    scenes = SCENE_LIST_RGBW_1000
                scenes = {**self._modes.as_dict(), **scenes}
            self._scenes = DictSelector(scenes, reverse=True)

            self._effect_list = list(scenes.keys()) + self._effect_list

        if self._color_data_wrapper is not None:
            color_data = self.dp_value(CONF_COLOR)
            # Write-only devices use the base64 raw color format.
            self._color_data_wrapper._use_raw = bool(
                is_write_only and not color_data
            )

            # Like the reference component, derive the HSV color type from the
            # cloud colour_data spec (per-channel min/max) so hue/sat remapping
            # adapts to the device's actual ranges (e.g. a 0-100 hue strip).
            if self._color_type_data is None:
                if (spec := self._device.color_data_spec) and "h" in spec:
                    self._color_type_data = ColorTypeData.from_config(spec)
                    self._color_data_wrapper._color_type_data = self._color_type_data

        if self.has_config(CONF_COLOR_MODE):
            if (wrapper := dp_wrapper_by_id(
                self._device, self._config.get(CONF_COLOR_MODE)
            )) and getattr(wrapper, "options", None):
                self._work_mode_range = wrapper.options

        if is_write_only and self._cached_status:
            self._status.update(self._cached_status)

    @property
    def extra_state_attributes(self):
        """Return entity specific state attributes to be saved.

        These attributes are then available for restore when the
        entity is restored at startup.
        """
        attributes = super().extra_state_attributes

        extra_attrs = (CONF_COLOR_MODE, CONF_COLOR, CONF_BRIGHTNESS, CONF_COLOR_TEMP)
        for attr in extra_attrs:
            dp = self._config.get(attr)
            if dp is not None and (state := self._status.get(dp)) is not None:
                attributes[f"raw_{attr}"] = state

        return attributes

    @property
    def is_on(self):
        """Return true if light is on."""
        return self._read_wrapper(self._switch_wrapper)

    async def async_turn_on(self, **kwargs):
        """Turn on or control the light."""
        commands = []
        if not self.is_on or self._write_only:
            commands.extend(self._switch_wrapper.get_update_commands(self._device, True))
        features = self.supported_features
        color_modes = self.supported_color_modes
        brightness = None
        color_mode = None

        if ATTR_EFFECT in kwargs and (features & LightEntityFeature.EFFECT):
            effect = kwargs[ATTR_EFFECT]
            scene = self._scenes.to_tuya(effect)
            if scene is not None:
                if scene.startswith(self._modes.scene) or scene in (
                    self._modes.white,
                    self._modes.color,
                ):
                    color_mode = scene
                else:
                    color_mode = self._modes.scene
                    if self._scene_wrapper is not None:
                        commands.extend(
                            self._scene_wrapper.get_update_commands(self._device, scene)
                        )
            elif effect in self._modes.as_list():
                color_mode = effect
            elif effect == SCENE_MUSIC:
                color_mode = self._modes.music

        if ATTR_BRIGHTNESS in kwargs and (
            ColorMode.BRIGHTNESS in color_modes
            or self._brightness_wrapper is not None
            or self._color_data_wrapper is not None
        ):
            brightness = map_range(
                int(kwargs[ATTR_BRIGHTNESS]),
                0,
                255,
                self._lower_brightness,
                self._upper_brightness,
            )
            brightness = max(brightness, self._lower_brightness)

            if self.is_color_mode and self._color_data_wrapper is not None:
                hsv = self._read_wrapper(self._color_data_wrapper)
                hs = hsv[:2] if hsv is not None else (0, 0)
                commands.extend(
                    self._color_data_wrapper.get_update_commands(
                        self._device, (hs[0], hs[1], brightness)
                    )
                )
                color_mode = self._modes.color
            else:
                if self._brightness_wrapper is not None:
                    commands.extend(
                        self._brightness_wrapper.get_update_commands(
                            self._device, int(kwargs[ATTR_BRIGHTNESS])
                        )
                    )
                color_mode = self._modes.white

        if ATTR_HS_COLOR in kwargs and ColorMode.HS in color_modes:
            if brightness is None:
                brightness = self._upper_brightness
            hs = kwargs[ATTR_HS_COLOR]
            if (
                hs[1] == 0
                and self._brightness_wrapper is not None
                and self._device.white_mode_supported
            ):
                commands.extend(
                    self._brightness_wrapper.get_update_commands(
                        self._device, brightness
                    )
                )
                color_mode = self._modes.white
            elif self._color_data_wrapper is not None:
                commands.extend(
                    self._color_data_wrapper.get_update_commands(
                        self._device, (hs[0], hs[1], brightness)
                    )
                )
                color_mode = self._modes.color

        if ATTR_COLOR_TEMP_KELVIN in kwargs and ColorMode.COLOR_TEMP in color_modes:
            if brightness is None:
                brightness = self._upper_brightness
            if self._color_temp_wrapper is not None:
                commands.extend(
                    self._color_temp_wrapper.get_update_commands(
                        self._device, int(kwargs[ATTR_COLOR_TEMP_KELVIN])
                    )
                )
            color_mode = self._modes.white
            if self._brightness_wrapper is not None:
                commands.extend(
                    self._brightness_wrapper.get_update_commands(
                        self._device, brightness
                    )
                )

        if ATTR_WHITE in kwargs and ColorMode.WHITE in color_modes:
            if brightness is None:
                brightness = self._upper_brightness
            color_mode = self._modes.white
            if self._brightness_wrapper is not None:
                commands.extend(
                    self._brightness_wrapper.get_update_commands(
                        self._device, brightness
                    )
                )

        if color_mode is not None and self._color_mode_wrapper is not None:
            commands.extend(
                self._color_mode_wrapper.get_update_commands(self._device, color_mode)
            )

        await self._async_send_commands(commands)

    async def async_turn_off(self, **kwargs):
        """Instruct the light to turn off."""
        await self._async_send_wrapper_updates(self._switch_wrapper, False)

    @property
    def brightness(self):
        """Return the brightness of the light."""
        if self._color_data_wrapper is not None and self.is_color_mode:
            hsv = self._read_wrapper(self._color_data_wrapper)
            return (
                None
                if hsv is None
                else round(
                    map_range(hsv[2], self._lower_brightness, self._upper_brightness)
                )
            )
        if self._brightness_wrapper is not None and (
            self.is_color_mode or self.is_white_mode
        ):
            return self._read_wrapper(self._brightness_wrapper)
        return None

    @property
    def color_temp_kelvin(self):
        """Return the color temperature value in Kelvin."""
        if self._color_temp_wrapper is None:
            return None
        return self._read_wrapper(self._color_temp_wrapper)

    @property
    def hs_color(self):
        """Return the hs_color of the light."""
        if self._color_data_wrapper is None:
            return None
        if self.is_color_mode:
            hsv = self._read_wrapper(self._color_data_wrapper)
            return None if hsv is None else [hsv[0], hsv[1]]
        if (
            ColorMode.HS in self.supported_color_modes
            and ColorMode.COLOR_TEMP not in self.supported_color_modes
        ):
            return [0, 0]
        return None

    @property
    def effect(self):
        """Return the current effect for this light."""
        if self.is_music_mode:
            return SCENE_MUSIC
        if self.is_scene_mode:
            color_mode = self.__get_color_mode()
            if color_mode != self._modes.scene:
                return self.__find_scene_by_scene_data(color_mode)
            effect = self.__find_scene_by_scene_data(self.dp_value(CONF_SCENE))
            if effect is None:
                effect = self.__find_scene_by_scene_data(color_mode)
            return effect
        if (color_mode := self.__get_color_mode()) in self._scenes.values:
            return self.__find_scene_by_scene_data(color_mode)
        return None

    @property
    def effect_list(self):
        """Return the list of supported effects for this light."""
        if len(self._effect_list) > 0:
            return self._effect_list
        return None

    @property
    def supported_color_modes(self) -> set[ColorMode] | set[str] | None:
        """Flag supported color modes."""
        color_modes: set[ColorMode] = set()

        if self.has_config(CONF_COLOR_TEMP):
            color_modes.add(ColorMode.COLOR_TEMP)
        elif self.has_config(CONF_BRIGHTNESS) and self._device.white_mode_supported:
            color_modes.add(ColorMode.WHITE)
        if self.has_config(CONF_COLOR):
            color_modes.add(ColorMode.HS)

        if color_modes == {ColorMode.WHITE}:
            return {ColorMode.BRIGHTNESS}

        if not color_modes:
            return {ColorMode.ONOFF}

        return color_modes

    @property
    def supported_features(self) -> LightEntityFeature:
        """Flag supported features."""
        supports = LightEntityFeature(0)
        if self.has_config(CONF_SCENE) or self.has_config(CONF_MUSIC_MODE):
            supports |= LightEntityFeature.EFFECT
        return supports

    @property
    def is_white_mode(self):
        """Return true if the light is in white mode."""
        color_mode = self.__get_color_mode()
        return color_mode is None or color_mode == self._modes.white

    @property
    def is_color_mode(self):
        """Return true if the light is in color mode.

        Mirrors the reference component's model: any work_mode that is not
        white, scene or music is treated as color (so US spelling "color"
        and "colour" both classify without alias tables).
        """
        color_mode = self.__get_color_mode()
        return color_mode is not None and not (
            self.is_white_mode or self.is_scene_mode or self.is_music_mode
        )

    @property
    def is_scene_mode(self):
        """Return true if the light is in scene mode."""
        color_mode = self.__get_color_mode()
        return (
            isinstance(color_mode, str)
            and color_mode.startswith(self._modes.scene)
        )

    @property
    def is_music_mode(self):
        """Return true if the light is in music mode."""
        color_mode = self.__get_color_mode()
        if color_mode is None:
            return False
        if color_mode == self._modes.music:
            return True
        if self._work_mode_range is not None:
            # Cloud-derived: music is any work_mode value named for music.
            return "music" in str(color_mode) or "dynamic" in str(color_mode)
        return color_mode in MODE_MUSIC_ALIASES

    @property
    def color_mode(self) -> ColorMode:
        """Return the color_mode of the light."""
        if len(self.supported_color_modes) == 1:
            return next(iter(self.supported_color_modes))

        if self.is_color_mode:
            return ColorMode.HS
        if self.is_white_mode:
            if self.has_config(CONF_COLOR_TEMP):
                return ColorMode.COLOR_TEMP
            return ColorMode.WHITE
        if (
            (self.is_scene_mode or self.is_music_mode)
            and ColorMode.HS in self.supported_color_modes
        ):
            return ColorMode.HS
        if self.brightness and ColorMode.BRIGHTNESS in self.supported_color_modes:
            return ColorMode.BRIGHTNESS
        if ColorMode.HS in self.supported_color_modes:
            return ColorMode.HS
        return next(iter(self.supported_color_modes))

    def __find_scene_by_scene_data(self, data):
        return (
            next(
                (i for i in self._effect_list if self._scenes.to_tuya(i) == data),
                None,
            )
            if data is not None
            else None
        )

    def __get_color_mode(self):
        if self._color_mode_wrapper is not None:
            return self._read_wrapper(self._color_mode_wrapper)
        return self._modes.white

    def status_restored(self, stored_state) -> None:
        """Device status was restored."""
        restore_attrs = (CONF_COLOR_MODE, CONF_COLOR, CONF_BRIGHTNESS, CONF_COLOR_TEMP)
        if self._write_only:
            for attr in restore_attrs:
                dp = self._config.get(attr)
                restored_value = stored_state.attributes.get(f"raw_{attr}")
                if None in (dp, restored_value):
                    continue
                self._cached_status[dp] = restored_value
                self._state = self._last_state


async_setup_entry = partial(async_setup_entry, DOMAIN, LocalTuyaLight, flow_schema)
