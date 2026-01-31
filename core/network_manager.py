"""
Dunamis IRC Bot - Network Manager

Copyright (C) 2026 Helenah, Helena Bolan <helenah2025@proton.me>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

from typing import Dict, Optional, List
from twisted.internet import reactor, ssl

from .logger import Logger
from .network_config import NetworkConfig
from .database_manager import DatabaseManager
from .factory import Factory
from .plugin_manager import PluginManager


class NetworkManager:
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.networks: Dict[int, NetworkConfig] = {}
        self.factories: Dict[int, Factory] = {}
        self.connectors: Dict[int, any] = {}
        self.connected_addresses: Dict[int, tuple] = {}
        self.plugin_manager = PluginManager()

    def load_networks(self) -> List[NetworkConfig]:
        networks = self.db.get_networks()
        for network in networks:
            self.networks[network.id] = network
        Logger.info(f"Loaded {len(networks)} network configurations")
        return networks

    def connect_network(self, network_id: int, address_idx: int = 0,
                       port_idx: int = 0) -> bool:
        if network_id not in self.networks:
            Logger.error(f"Network {network_id} not found")
            return False

        if network_id in self.connectors:
            Logger.warning(f"Already connected to network {network_id}")
            return False

        network_config = self.networks[network_id]

        # Check if auto-connect is disabled
        if not network_config.auto_connect:
            Logger.info(f"Skipping network {network_config.name} (auto_connect disabled)")
            return False

        factory = Factory(network_config, self.db, self.plugin_manager, self)
        self.factories[network_id] = factory

        try:
            # Get address and port to try
            if address_idx >= len(network_config.addresses):
                address_idx = 0
            address = network_config.addresses[address_idx]

            if network_config.enable_ssl:
                if port_idx >= len(network_config.ssl_ports):
                    port_idx = 0
                port = network_config.ssl_ports[port_idx]

                connector = reactor.connectSSL(
                    address,
                    port,
                    factory,
                    ssl.ClientContextFactory()
                )
            else:
                if port_idx >= len(network_config.ports):
                    port_idx = 0
                port = network_config.ports[port_idx]

                connector = reactor.connectTCP(
                    address,
                    port,
                    factory
                )

            self.connectors[network_id] = connector
            # Store the connected address and port
            self.connected_addresses[network_id] = (address, port)
            Logger.info(f"Connecting to network: {network_config.name} ({address}:{port})")
            return True

        except Exception as e:
            Logger.error(f"Failed to connect to network {network_id}: {e}")
            return False

    def disconnect_network(self, network_id: int, reconnect: bool = False) -> bool:
        if network_id not in self.connectors:
            Logger.warning(f"Not connected to network {network_id}")
            return False

        try:
            connector = self.connectors[network_id]
            network_config = self.networks[network_id]

            # Check if auto-reconnect should be honored
            if not reconnect and not network_config.auto_reconnect:
                if network_id in self.factories:
                    self.factories[network_id].should_reconnect = False

            connector.disconnect()

            if not reconnect:
                del self.connectors[network_id]
                if network_id in self.factories:
                    del self.factories[network_id]
                if network_id in self.connected_addresses:
                    del self.connected_addresses[network_id]

            Logger.info(f"Disconnected from network: {network_config.name}")
            return True

        except Exception as e:
            Logger.error(f"Failed to disconnect from network {network_id}: {e}")
            return False

    def reconnect_network(self, network_id: int) -> bool:
        if network_id in self.connectors:
            if not self.disconnect_network(network_id, reconnect=True):
                return False

        return self.connect_network(network_id)

    def get_network_status(self, network_id: int) -> Optional[Dict]:
        if network_id not in self.networks:
            return None

        network = self.networks[network_id]
        is_connected = network_id in self.connectors

        status = {
            "id": network.id,
            "name": network.name,
            "addresses": network.addresses,
            "ports": network.ports,
            "ssl_ports": network.ssl_ports,
            "ssl": network.enable_ssl,
            "auto_connect": network.auto_connect,
            "auto_reconnect": network.auto_reconnect,
            "connected": is_connected,
            "auth_mechanism": network.auth_mechanism,
        }

        # Add connected server info if connected
        if is_connected and network_id in self.connected_addresses:
            address, port = self.connected_addresses[network_id]
            status["connected_address"] = address
            status["connected_port"] = port

        if is_connected and network_id in self.factories:
            factory = self.factories[network_id]
            if hasattr(factory, 'protocol') and factory.protocol:
                proto = factory.protocol
                status["nickname"] = getattr(proto, 'nickname', None)
                status["channels"] = getattr(proto, 'joined_channels', [])
                status["sasl_authenticated"] = getattr(proto, 'sasl_authenticated', False)

        return status

    def list_networks(self) -> List[Dict]:
        return [self.get_network_status(net_id) for net_id in self.networks.keys()]

    def connect_all(self):
        connected = 0
        for network_id, network in self.networks.items():
            if network.auto_connect:
                if self.connect_network(network_id):
                    connected += 1
        Logger.info(f"Connected to {connected} networks")

    def disconnect_all(self):
        for network_id in list(self.connectors.keys()):
            self.disconnect_network(network_id)

    def get_factory(self, network_id: int) -> Optional[Factory]:
        return self.factories.get(network_id)

    def get_protocol(self, network_id: int):
        factory = self.get_factory(network_id)
        if factory and hasattr(factory, 'protocol'):
            return factory.protocol
        return None

    def reload_network_config(self, network_id: int) -> bool:
        try:
            networks = self.db.get_networks()
            for network in networks:
                if network.id == network_id:
                    self.networks[network_id] = network
                    Logger.info(f"Reloaded configuration for network {network_id}")
                    return True

            Logger.warning(f"Network {network_id} not found in database")
            return False
        except Exception as e:
            Logger.error(f"Failed to reload network config: {e}")
            return False

    def get_network_by_name(self, name: str) -> Optional[NetworkConfig]:
        for network in self.networks.values():
            if network.name.lower() == name.lower():
                return network
        return None
