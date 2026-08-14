"""Code shared between all platforms."""

import logging
from enum import Enum
from typing import Any, Coroutine, Callable

from homeassistant.core import HomeAssistant, State
from homeassistant.config_entries import ConfigEntry

from homeassistant.const import (
    CONF_DEVICES,
    CONF_DEVICE_CLASS,
    CONF_ENTITIES,
    CONF_ENTITY_CATEGORY,
    CONF_FRIENDLY_NAME,
    CONF_HOST,
    CONF_ICON,
    CONF_ID,
    CONF_PLATFORM,
    EntityCategory,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
from homeassistant.core import callback

from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .core import pytuya
from .core.mappings import get_mapping_by_device
from .const import get_device_key
from .coordinator import HassLocalTuyaData, TuyaDevice
from .const import (
    ATTR_STATE,
    CONF_DEFAULT_VALUE,
    CONF_ENTITY_ENABLED_DEFAULT,
    CONF_ID,
    CONF_ICONS,
    CONF_IS_AVAILABLE,
    CONF_NODE_ID,
    CONF_PASSIVE_ENTITY,
    CONF_RESTORE_ON_RECONNECT,
    CONF_SCALING,
    CONF_OFFSET,
    DOMAIN,
    LOCALTUYA_DISCOVERY_NEW,
    RESTORE_STATES,
    TRANSPORT_BLE,
    DeviceConfig,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    domain: str,
    entity_class: Any,
    flow_schema: Callable,
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    async_setup_services: Coroutine[HomeAssistant, list, None] = None,
):
    """Set up a Tuya platform based on a config entry.

    This is a generic method and each platform should lock domain and
    entity_class with functools.partial.
    """
    entities = []
    hass_entry_data: HassLocalTuyaData = hass.data[DOMAIN][config_entry.entry_id]

    for dev_id in config_entry.data[CONF_DEVICES]:
        dev_entry: dict = config_entry.data[CONF_DEVICES][dev_id]

        host = get_device_key(dev_entry)
        node_id = dev_entry.get(CONF_NODE_ID)
        device_key = f"{host}_{node_id}" if node_id else host

        if device_key not in hass_entry_data.devices:
            continue

        entities_to_setup: list[tuple[dict, Any]] = [
            (entity, None)
            for entity in dev_entry[CONF_ENTITIES]
            if entity[CONF_PLATFORM] == domain
        ]

        if not entities_to_setup:
            device: TuyaDevice = hass_entry_data.devices[device_key]
            # No manual entities: resolve via the single runtime resolver —
            # BLE per-product overrides first, then the shared category-table
            # derivation (definition-driven, both transports).
            entities_to_setup = _entity_specs_for_device(device, domain, dev_entry)

        if entities_to_setup:
            device: TuyaDevice = hass_entry_data.devices[device_key]
            dps_config_fields = list(get_dps_for_platform(flow_schema))

            for entity_config, description in entities_to_setup:
                # Add DPS used by this platform to the request list
                for dp_conf in dps_config_fields:
                    if dp_conf in entity_config:
                        device.dps_to_request[entity_config[dp_conf]] = None

                kwargs = {
                    # we need add_entites_callback in-case we want to add sub-entites, such as electric sensor "phase_a"
                    "add_entites_callback": async_add_entities,
                    "config": entity_config,
                }
                if description is not None:
                    kwargs["description"] = description
                entities.append(
                    entity_class(
                        device,
                        dev_entry,
                        entity_config[CONF_ID],
                        **kwargs,
                    )
                )
    # Once the entities have been created, add to the TuyaDevice instance
    if entities:
        device.add_entities(entities)
        async_add_entities(entities)

        if async_setup_services:
            await async_setup_services(hass, entities)

    # Runtime discovery: devices that become available after setup (e.g. a BLE
    # device that paired/bound at runtime) fire LOCALTUYA_DISCOVERY_NEW, so
    # this platform creates entities on the fly. Mirrors core tuya's
    # async_discover_device flow (switch.py:933-951).
    @callback
    def _async_discover_device(device_keys: list[str]) -> None:
        """Create entities for devices that became available at runtime."""
        discovered: list[LocalTuyaEntity] = []
        for device_key in device_keys:
            device = hass_entry_data.devices.get(device_key)
            if device is None or device.ble_device is None:
                continue
            dev_entry = config_entry.data[CONF_DEVICES].get(device.id)
            if dev_entry is None:
                continue
            if any(
                entity.get(CONF_PLATFORM) == domain
                for entity in dev_entry.get(CONF_ENTITIES, [])
            ):
                continue
            for entity_config, description in _entity_specs_for_device(
                device, domain, dev_entry
            ):
                for dp_conf in dps_config_fields:
                    if dp_conf in entity_config:
                        device.dps_to_request[entity_config[dp_conf]] = None
                kwargs = {
                    "add_entites_callback": async_add_entities,
                    "config": entity_config,
                }
                if description is not None:
                    kwargs["description"] = description
                discovered.append(
                    entity_class(
                        device,
                        dev_entry,
                        entity_config[CONF_ID],
                        **kwargs,
                    )
                )
        if discovered:
            device.add_entities(discovered)
            async_add_entities(discovered)

    config_entry.async_on_unload(
        async_dispatcher_connect(hass, LOCALTUYA_DISCOVERY_NEW, _async_discover_device)
    )


def get_dps_for_platform(flow_schema):
    """Return config keys for all platform keys that depends on a datapoint."""
    for key, value in flow_schema(None).items():
        if hasattr(value, "container") and value.container is None:
            yield key.schema


def _auto_entities_for_device(
    device: TuyaDevice, domain: str, dev_entry: dict
) -> list[dict]:
    """Auto-generate entity configs for a BLE device from its product mapping.

    Only entities whose datapoint exists on the device (or that are marked
    ``force_add``) are returned. Generated configs are injected into
    ``dev_entry[CONF_ENTITIES]`` so ``get_entity_config`` can resolve them.
    """
    ble_device = device.ble_device
    if ble_device is None:
        return []

    existing_ids = {
        ent.get(CONF_ID)
        for ent in dev_entry.get(CONF_ENTITIES, [])
        if ent.get(CONF_PLATFORM) == domain
    }
    generated = []
    for mapping in get_mapping_by_device(ble_device):
        if mapping.platform.value != domain:
            continue
        if not mapping.force_add and not ble_device.datapoints.has_id(
            mapping.dp_id, mapping.dp_type
        ):
            continue
        config = dict(mapping.config)
        config[CONF_ID] = str(mapping.dp_id)
        config[CONF_PLATFORM] = domain
        if config[CONF_ID] in existing_ids:
            continue
        generated.append(config)

    if generated:
        dev_entry.setdefault(CONF_ENTITIES, []).extend(generated)
    return generated


def get_entity_config(config_entry, dp_id) -> dict:
    """Return entity config for a given DPS id."""
    for entity in config_entry[CONF_ENTITIES]:
        if entity[CONF_ID] == dp_id:
            return entity
    raise Exception(f"missing entity config for id {dp_id}")


def _dpcode_to_id(device) -> dict[str, Any]:
    """Return dpcode → dp_id from the device's function/status_range specs."""
    spec: dict[str, Any] = {}
    for source in (
        getattr(device, "function", {}) or {},
        getattr(device, "status_range", {}) or {},
    ):
        for code, fn in source.items():
            if isinstance(fn, dict):
                dp_id = fn.get("dp_id")
            else:
                dp_id = getattr(fn, "dp_id", None)
            if dp_id is not None:
                spec[code] = dp_id
    return spec


def _resolve_dpcode(value: Any, spec: dict) -> str | None:
    """Resolve a DPCode (str/Enum/tuple) to a code present in the device spec."""
    if value is None:
        return None
    if isinstance(value, tuple):
        for alt in value:
            if (code := _resolve_dpcode(alt, spec)) is not None:
                return code
        return None
    code = value.value if isinstance(value, Enum) else value
    return code if code in spec else None


def _dp_value_strings(device, code: str | None, dp_id: str | None) -> list[str]:
    """Return lowercase candidate value strings for a DP.

    Used to gate descriptions carrying ``contains_any`` against the device's
    actual reported value (live status first, then the persisted cloud value
    snapshot). Mirrors the legacy ``gen_localtuya_entities`` value check, which
    matched the ``contains_any`` conditions against the DP value string.
    """
    values: list[str] = []
    status = getattr(device, "status", {}) or {}
    for key in (code, str(dp_id) if dp_id is not None else None):
        if key is not None and status.get(key) is not None:
            values.append(str(status[key]).lower())
    for specs in (
        getattr(device, "function", {}) or {},
        getattr(device, "status_range", {}) or {},
    ):
        if code is None or (spec := specs.get(code)) is None:
            continue
        raw = spec.get("value") if isinstance(spec, dict) else getattr(spec, "value", None)
        if raw is not None:
            values.append(str(raw).lower())
    return values


def _contains_any_matches(
    device, description, code: str | None, dp_id: str | None
) -> bool:
    """Return whether a description's ``contains_any`` gate is satisfied.

    A description with ``contains_any`` only applies when the device's primary
    DP value contains one of the listed conditions (e.g. the relay_status
    ``power_on/off/last`` vs ``on/off/memory`` vs ``0/1/2`` variants).
    Descriptions without the gate always apply.
    """
    contains_any = getattr(description, "contains_any", None)
    if not contains_any:
        return True
    values = _dp_value_strings(device, code, dp_id)
    if not values:
        return False
    return any(cond in value for cond in contains_any for value in values)


def entity_config_from_description(
    device, description, platform
) -> tuple[dict, str | None]:
    """Build a legacy ``_config`` dict from a category-table description.

    Maps the description's DPCodes to dp_ids via the device's
    function/status_range specs, merges ``data`` + ``entity_configs``, and
    returns ``(config, primary_dp_id)``. The primary dp_id is None when the
    primary DP is absent from the device spec (core's spec gate). This is the
    description → ``_config`` compatibility adapter (SPEC_DEFINITION_DRIVEN_RUNTIME
    D3): platforms can read the same ``self._config`` surface during the
    migration to description-driven wrappers.
    """
    config: dict[str, Any] = {}

    for key, value in (getattr(description, "data", {}) or {}).items():
        if value not in (None, "", "None"):
            config[key] = value

    spec = _dpcode_to_id(device)
    primary_id: str | None = None
    primary_code: str | None = None
    for key, value in (getattr(description, "localtuya_conf", {}) or {}).items():
        if (code := _resolve_dpcode(value, spec)) is None:
            if key == CONF_ID:
                return config, None
            continue
        dp_id = str(spec[code])
        if key == CONF_ID:
            primary_id = dp_id
            primary_code = code
        config[key] = dp_id

    if primary_id is not None and not _contains_any_matches(
        device, description, primary_code, primary_id
    ):
        return config, None

    config[CONF_PLATFORM] = platform
    config[CONF_ENTITY_ENABLED_DEFAULT] = True

    for key, value in (getattr(description, "entity_configs", {}) or {}).items():
        if hasattr(value, "default_value"):
            value = value.default_value
        config[key] = value

    return config, primary_id


def descriptions_for_platform(device, domain: str) -> list:
    """Return the category-table descriptions for a platform domain.

    Looks up the device's cloud category in the ``ha_entities`` tables. Returns
    an empty list when the device has no category or the platform has no table.
    """
    category = getattr(device, "category", None)
    if not category:
        return []
    from .core.ha_entities import DATA_PLATFORMS  # local import (import cycle)

    for platform, table in DATA_PLATFORMS.items():
        if platform.value == domain:
            return list(table.get(category, ()))
    return []


def _described_entity_specs(device, domain: str) -> list[tuple[dict, Any]]:
    """Build ``(config, description)`` pairs from the device's category tables.

    Each description is resolved through ``entity_config_from_description``;
    descriptions whose primary DP is absent from the device spec (core's spec
    gate) are skipped.
    """
    specs = []
    seen_ids: set[str] = set()
    for description in descriptions_for_platform(device, domain):
        config, dp_id = entity_config_from_description(device, description, domain)
        if dp_id is None or dp_id in seen_ids:
            continue
        seen_ids.add(dp_id)
        specs.append((config, description))
    return specs


def _entity_specs_for_device(
    device: TuyaDevice, domain: str, dev_entry: dict
) -> list[tuple[dict, Any]]:
    """Resolve ``(config, description)`` specs for a device with no manual entities.

    The single runtime resolver for auto-configured entities: BLE devices first
    consult their per-product hardcoded overrides (``mappings.py``), then fall
    back to the shared category-table derivation; Ethernet/cloud devices use
    the category tables directly. Both transports end on the same
    ``_described_entity_specs`` path, so wrappers resolve by dpcode from the
    description (core parity) with manual ``dps`` as the fallback.
    """
    if device.ble_device is None:
        return _described_entity_specs(device, domain)

    specs = [
        (config, None)
        for config in _auto_entities_for_device(device, domain, dev_entry)
    ]
    if specs:
        return specs
    return _described_entity_specs(device, domain)


class LocalTuyaEntity(RestoreEntity, pytuya.ContextualLogger):
    """Representation of a Tuya entity."""

    _attr_device_class = None
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        device: TuyaDevice,
        device_config: dict,
        dp_id: str,
        logger,
        config: dict | None = None,
        **kwargs,
    ):
        """Initialize the Tuya entity.

        ``config`` is the resolved entity config dict. When omitted (the
        config-driven path) it is looked up from ``device_config`` by ``dp_id``;
        the definition-driven path passes the description-derived config (see
        ``entity_config_from_description``) so the same ``self._config`` surface
        works during the migration.
        """
        super().__init__()
        self._device = device
        self._device_config = DeviceConfig(device_config)
        self._config = (
            config if config is not None else get_entity_config(device_config, dp_id)
        )
        self._dp_id = dp_id
        # Keep subclass-set keys (e.g. BLE dpcode keys); derive platform_dp_id otherwise.
        if getattr(self, "_attr_translation_key", None) is None:
            self._attr_translation_key = (
                f"{self._config.get(CONF_PLATFORM)}_{self._dp_id}"
            )
        self._status = {}
        self._state = None
        self._last_state = None
        self._stored_states: State | None = None
        self.hass = device.hass
        self.componet_add_entities: AddEntitiesCallback = kwargs.get(
            "add_entites_callback"
        )
        self._loaded = False

        # Default value is available to be provided by Platform entities if required
        self._default_value = self._config.get(CONF_DEFAULT_VALUE)

        # Optional per-DP callback: is_available gates availability on top of
        # the connection status.
        self._is_available = kwargs.get("is_available") or self._config.get(
            CONF_IS_AVAILABLE
        )

        """ Restore on connect setting is available to be provided by Platform entities
        if required"""
        dev = self._device_config
        self.set_logger(logger, dev.id, dev.enable_debug, dev.name)
        self.debug(f"Initialized {self._config.get(CONF_PLATFORM)} [{self.name}]")

    async def async_added_to_hass(self):
        """Subscribe localtuya events."""
        await super().async_added_to_hass()

        self.debug(f"Adding {self.entity_id} with configuration: {self._config}")

        stored_data = await self.async_get_last_state()
        if stored_data:
            self._stored_states = stored_data
            self.status_restored(stored_data)

        async def _update_handler(
            status: dict | None,
            updated_status_properties: list[str] | None = None,
            dp_timestamps: dict[str, int] | None = None,
        ):
            """Update entity state when status was updated.

            Mirrors core's ``_handle_state_update``: the HA state write is
            skipped when the coordinator delivers a known delta and the
            platform's ``_process_device_update`` says to skip it.
            """
            last_status = self._status.copy()

            self._status = {} if status is None else {**self._status, **status}

            if not self._loaded:
                self._loaded = True
                self.connection_made()

            if status != last_status:
                if status:
                    self.status_updated()

                if updated_status_properties is None or await self._process_device_update(
                    updated_status_properties, dp_timestamps
                ):
                    self.schedule_update_ha_state()

        signal = f"localtuya_{self._device_config.id}"

        self.async_on_remove(
            async_dispatcher_connect(self.hass, signal, _update_handler)
        )

        signal = f"localtuya_entity_{self._device_config.id}"
        async_dispatcher_send(self.hass, signal, self.entity_id)

    @property
    def extra_state_attributes(self):
        """Return entity specific state attributes to be saved.

        These attributes are then available for restore when the
        entity is restored at startup.
        """
        attributes = {}
        if self._state is not None:
            attributes[ATTR_STATE] = self._state
        elif self._last_state is not None:
            attributes[ATTR_STATE] = self._last_state

        self.debug(f"Entity {self.name} - Additional attributes: {attributes}")
        return attributes

    @property
    def device_info(self):
        """Return device information for the device registry."""
        device_config = self._device_config
        device_info = DeviceInfo(
            # Serial numbers are unique identifiers within a specific domain
            identifiers={(DOMAIN, f"local_{device_config.id}")},
            name=device_config.name,
            manufacturer="Tuya",
            model=f"{device_config.model} ({device_config.id})",
            sw_version=device_config.protocol_version,
        )
        if self._device.is_subdevice and self._device.id != self._device.gateway.id:
            if gateway_device := dr.async_get(
                self.hass
            ).async_get_device_by_identifier(
                (DOMAIN, f"local_{self._device.gateway.id}"),
                self._device.config_entry.entry_id,
            ):
                device_info["via_device_id"] = gateway_device.id
        return device_info

    @property
    def name(self) -> str:
        """Get name of Tuya entity."""
        return getattr(self, "_attr_name", self._config.get(CONF_FRIENDLY_NAME))

    @property
    def icon(self) -> str | None:
        """Icon of the entity."""
        if getattr(self, "_attr_icon", None) is not None:
            return self._attr_icon
        if icons := self._config.get(CONF_ICONS):
            if isinstance(self._state, int) and 0 <= self._state < len(icons):
                return icons[self._state]
        return self._config.get(CONF_ICON, None)

    @property
    def unique_id(self) -> str:
        """Return unique device identifier."""
        if getattr(self, "_attr_unique_id") is not None:
            return self._attr_unique_id

        return f"local_{self._device_config.id}_{self._dp_id}"

    @property
    def available(self) -> bool:
        """Return if device is available or not."""
        result = (len(self._status) > 0) or self._device.connected
        if result and self._is_available:
            result = self._is_available()
        return result

    @property
    def entity_category(self) -> str:
        """Return the category of the entity."""
        if category := self._config.get(CONF_ENTITY_CATEGORY):
            return EntityCategory(category) if category != "None" else None
        else:
            # Set Default values for unconfigured devices.
            if platform := self._config.get(CONF_PLATFORM):
                # Call default_category from config_flow  to set default values!
                # This will be removed after a while, this is only made to convert who came from main integration.
                # new users will be forced to choose category from config_flow.
                from .config_flow import default_category

                return default_category(platform)
        return None

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled when first added."""
        return self._config.get(CONF_ENTITY_ENABLED_DEFAULT, True)

    @property
    def device_class(self):
        """Return the class of this device."""
        attr_device_class = getattr(self, "_attr_device_class")
        return attr_device_class or self._config.get(CONF_DEVICE_CLASS)

    def has_config(self, attr) -> bool:
        """Return if a config parameter has a valid value."""
        value = self._config.get(attr, "-1")
        return value is not None and value != "-1"

    def dp_value(self, key, default=None) -> Any | None:
        """Return cached value for DPS index or Entity Config Key. else default None"""
        requested_dp = str(key)
        # If requested_dp in DP ID, get cached value.
        if (value := self._status.get(requested_dp)) or value is not None:
            return value

        # If requested_dp is an config key get config dp then get cached value.
        if (conf_key := self._config.get(requested_dp)) or conf_key is not None:
            if (value := self._status.get(conf_key)) or value is not None:
                return value

        if value is None:
            value = default
            # self.debug(f"{self.name}: is requesting unknown DP Value {key}", force=True)

        return value

    def status_updated(self) -> None:
        """Device status was updated.

        Override in subclasses and update entity specific state.
        """
        state = self.dp_value(self._dp_id)
        self._state = state

        # Keep record in last_state as long as not during connection/re-connection,
        # as last state will be used to restore the previous state
        if (state is not None) and (not self._device.is_connecting):
            self._last_state = state

    def _read_wrapper(self, wrapper) -> Any | None:
        """Read the wrapper's device status (core-tuya parity).

        Mirrors ``TuyaEntity._read_wrapper``; the wrapper resolves its value
        from ``device.status`` (dpcode-keyed) with type conversion.
        """
        if wrapper is None:
            return None
        return wrapper.read_device_status(self._device)

    async def _async_send_commands(self, commands: list[dict]) -> None:
        """Send a list of DP update commands to the device (local transport).

        Core sends ``{code, dp_id, value}`` command dicts over MQTT; we send
        the same dicts over BLE/Ethernet via ``TuyaDevice.set_dp``.
        """
        if not commands:
            return
        for command in commands:
            await self._device.set_dp(command["value"], command["dp_id"])

    async def _async_send_wrapper_updates(self, wrapper, value) -> None:
        """Send a wrapper-generated command to the device (core-tuya parity)."""
        if wrapper is None:
            return
        await self._async_send_commands(wrapper.get_update_commands(self._device, value))

    async def _process_device_update(
        self,
        updated_status_properties: list[str],
        dp_timestamps: dict[str, int] | None,
    ) -> bool:
        """Called when Tuya device sends an update with updated properties.

        Returns True if the Home Assistant state should be written,
        or False if the state write should be skipped.
        """
        return True

    def status_restored(self, stored_state: State) -> None:
        """Device status was restored.

        Override in subclasses and update entity specific state.
        """
        raw_state = stored_state.attributes.get(ATTR_STATE)
        if raw_state is not None:
            self._last_state = raw_state
            self.debug(
                f"Restoring state for entity: {self.name} - state: {str(self._last_state)}"
            )

    def connection_made(self):
        """The connection has made with the device and status retrieved. configure entity based on it.

        Override in subclasses and update entity initialization based on detected DPS.
        """
        stored_data = self._stored_states
        if self._status == RESTORE_STATES and stored_data:
            self._status.pop("0", True)
            if self._dp_id in self._status:
                return
            if stored_data.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                self.debug(f"{self.name}: Restore state: {stored_data.state}")
                self._status[self._dp_id] = stored_data.state

    def default_value(self):
        """Return default value of this entity.

        Override in subclasses to specify the default value for the entity.
        """
        # Check if default value has been set - if not, default to the entity defaults.
        if self._default_value is None:
            self._default_value = self.entity_default_value()

        return self._default_value

    def entity_default_value(self):  # pylint: disable=no-self-use
        """Return default value of the entity type.

        Override in subclasses to specify the default value for the entity.
        """
        return 0

    def scale(self, value, scale_only=False):
        """Return the scaled factor of the value, else same value."""
        scale_factor = self._config.get(CONF_SCALING)
        offset = self._config.get(CONF_OFFSET)
        if isinstance(value, (int, float)):
            if scale_factor is not None:
                value = value * scale_factor
            if not scale_only and offset is not None:
                value = value + offset
            value = round(value, 2)

        return value

    async def restore_state_when_connected(self) -> None:
        """Restore if restore_on_reconnect is set, or if no status has been yet found.

        Which indicates a DPS that needs to be set before it starts returning
        status.
        """
        restore_on_reconnect = self._config.get(CONF_RESTORE_ON_RECONNECT, False)
        passive_entity = self._config.get(CONF_PASSIVE_ENTITY, False)
        dp_id = str(self._dp_id)

        if not restore_on_reconnect and (dp_id in self._status or not passive_entity):
            self.debug(
                f"Entity {self.name} (DP {self._dp_id}) - Not restoring as restore on reconnect is "
                + "disabled for this entity and the entity has an initial status "
                + "or it is not a passive entity"
            )
            return

        self.debug(f"Attempting to restore state for entity: {self.name}")
        # Attempt to restore the current state - in case reset.
        restore_state = self._state

        # If no state stored in the entity currently, go from last saved state
        if (restore_state == STATE_UNKNOWN) | (restore_state is None):
            self.debug("No current state for entity")
            restore_state = self._last_state

        # If no current or saved state, then use the default value
        if restore_state is None:
            if passive_entity:
                self.debug("No last restored state - using default")
                restore_state = self.default_value()
            else:
                self.debug("Not a passive entity and no state found - aborting restore")
                return

        self.debug(
            f"Entity {self.name} (DP {self._dp_id}) - Restoring state: {str(restore_state)}"
        )

        # Manually initialise
        await self._device.set_dp(restore_state, self._dp_id)
