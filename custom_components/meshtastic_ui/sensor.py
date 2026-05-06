"""Sensor platform for Meshtastic UI."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_NEW_MESSAGE
from .store import MeshtasticUiStore


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Meshtastic UI sensors."""
    domain_data = hass.data.get(DOMAIN, {})
    entries = domain_data.get("entries", {})
    entry_data = entries.get(entry.entry_id)
    # Backwards-compat for tests that still build the old singleton dict.
    if entry_data is None and "store" in domain_data:
        entry_data = domain_data
    if entry_data is None:
        return
    store: MeshtasticUiStore = entry_data["store"]
    async_add_entities(
        [
            MeshMessagesTodaySensor(store, entry.entry_id),
            MeshActiveNodesSensor(store, entry.entry_id),
        ]
    )


class _PerEntrySensor(SensorEntity):
    """Base for sensors that filter signal payloads by entry_id."""

    _attr_has_entity_name = True

    def __init__(self, store: MeshtasticUiStore, entry_id: str) -> None:
        self._store = store
        self._entry_id = entry_id

    @callback
    def _matches_entry(self, data: Any) -> bool:
        if isinstance(data, dict):
            event_entry_id = data.get("entry_id")
            return event_entry_id is None or event_entry_id == self._entry_id
        return True


class MeshMessagesTodaySensor(_PerEntrySensor):
    """Sensor tracking total messages received today."""

    _attr_name = "Messages Today"
    _attr_icon = "mdi:message-text"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = "messages"

    def __init__(self, store: MeshtasticUiStore, entry_id: str) -> None:
        super().__init__(store, entry_id)
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_messages_today"

    @property
    def native_value(self) -> int:
        """Return today's message count."""
        return self._store.messages_today

    async def async_added_to_hass(self) -> None:
        """Subscribe to message updates."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_NEW_MESSAGE, self._handle_new_message
            )
        )

    @callback
    def _handle_new_message(self, data: Any) -> None:
        """Update when a new message arrives for this entry's radio."""
        if not self._matches_entry(data):
            return
        self.async_write_ha_state()


class MeshActiveNodesSensor(_PerEntrySensor):
    """Sensor tracking active nodes (seen within 1 hour)."""

    _attr_name = "Active Nodes"
    _attr_icon = "mdi:access-point-network"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "nodes"

    def __init__(self, store: MeshtasticUiStore, entry_id: str) -> None:
        super().__init__(store, entry_id)
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_active_nodes"

    @property
    def native_value(self) -> int:
        """Return count of active nodes."""
        return self._store.active_nodes_count

    async def async_added_to_hass(self) -> None:
        """Subscribe to message updates to refresh node counts."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_NEW_MESSAGE, self._handle_update
            )
        )

    @callback
    def _handle_update(self, data: Any) -> None:
        """Refresh when activity occurs for this entry's radio."""
        if not self._matches_entry(data):
            return
        self.async_write_ha_state()
