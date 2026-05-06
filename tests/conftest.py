"""Shared fixtures for Meshtastic UI tests."""

from __future__ import annotations

from collections import deque
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.meshtastic_ui.connection import (
    ConnectionState,
    ConnectionType,
    MeshtasticConnection,
)
from custom_components.meshtastic_ui.const import (
    DOMAIN,
    TS_MAX_POINTS,
)
from custom_components.meshtastic_ui.store import MeshtasticUiStore


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests."""
    yield


@pytest.fixture(autouse=True)
def mock_hass_frontend():
    """Mock the frontend component setup to avoid needing hass_frontend package."""
    with patch(
        "homeassistant.components.frontend.async_setup",
        AsyncMock(return_value=True),
    ):
        yield


@pytest.fixture
def store(hass: HomeAssistant) -> MeshtasticUiStore:
    """Create a MeshtasticUiStore without loading from disk."""
    s = MeshtasticUiStore(hass)
    s._store = MagicMock()
    s._store.async_delay_save = MagicMock()
    s._store.async_load = AsyncMock(return_value=None)
    return s


@pytest.fixture
def mock_connection() -> MagicMock:
    """Create a mock MeshtasticConnection."""
    conn = MagicMock(spec=MeshtasticConnection)
    conn.state = ConnectionState.CONNECTED
    conn.connection_type = ConnectionType.TCP
    conn.interface = MagicMock()
    conn.nodes = {}
    conn.my_info = {
        "num": 305419896,
        "user": {"longName": "TestNode", "shortName": "TN", "hwModel": "TBEAM"},
    }
    conn.metadata = {"firmwareVersion": "2.5.0"}

    conn.async_connect = AsyncMock()
    conn.async_disconnect = AsyncMock()
    conn.async_send_text = AsyncMock(return_value=12345)
    conn.async_send_traceroute = AsyncMock()
    conn.async_request_position = AsyncMock()
    conn.async_get_config = AsyncMock(return_value={
        "local_config": {}, "module_config": {}, "channels": [],
        "owner": {}, "metadata": {},
    })
    conn.async_set_config = AsyncMock()
    conn.async_set_channel = AsyncMock()
    conn.async_set_owner = AsyncMock()
    conn.async_device_action = AsyncMock()
    conn.async_send_waypoint = AsyncMock(return_value=99)
    conn.async_delete_waypoint = AsyncMock()
    conn.async_node_admin = AsyncMock()

    conn.register_message_callback = MagicMock(return_value=MagicMock())
    conn.register_node_update_callback = MagicMock(return_value=MagicMock())
    conn.register_connection_change_callback = MagicMock(return_value=MagicMock())

    return conn


@pytest.fixture
def mock_config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Create a MockConfigEntry for TCP connection."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "connection_type": "tcp",
            "tcp_hostname": "192.168.1.100",
            "tcp_port": 4403,
        },
        unique_id=DOMAIN,
        title="Meshtastic (192.168.1.100)",
    )
    entry.add_to_hass(hass)
    return entry


_TS_SERIES_KEYS = ("airtimeTx", "battery", "channelUtil", "packetRx", "packetTx")
_PACKET_TYPE_KEYS = ("nodeinfo", "other", "position", "routing", "telemetry", "text")


@pytest.fixture
def hass_data(store: MeshtasticUiStore, mock_connection: MagicMock) -> dict:
    """Create a minimal hass.data[DOMAIN] dict for testing handlers."""
    return {
        "entry_id": "_legacy",
        "title": "Meshtastic Radio",
        "config": {},
        "store": store,
        "ts_store": MagicMock(),
        "connection": mock_connection,
        "unsub_callbacks": [],
        "pending_acks": {},
        "nodeinfo_cooldowns": {},
        "local_stats": {},
        "ts": {
            "data": {k: deque(maxlen=TS_MAX_POINTS) for k in _TS_SERIES_KEYS},
            "packetTypes": {k: deque(maxlen=TS_MAX_POINTS) for k in _PACKET_TYPE_KEYS},
            "snapshots": {"channelUtil": 0.0, "airtimeTx": 0.0, "battery": 0.0},
            "accumulators": {"packetTx": 0, "packetRx": 0},
            "packetTypeAccum": {k: 0 for k in _PACKET_TYPE_KEYS},
            "local_node_num": 305419896,
        },
    }
