"""
Dunamis IRC Bot - Factory

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

from typing import Optional
from twisted.internet import reactor, protocol

from .logger import Logger
from .network_config import NetworkConfig
from .database_manager import DatabaseManager
from .protocol import Protocol
from .plugin_manager import PluginManager


class Factory(protocol.ClientFactory):
    protocol_class = Protocol

    def __init__(self, config: NetworkConfig, db: DatabaseManager,
                 plugin_manager: Optional[PluginManager] = None,
                 network_manager = None):
        self.config = config
        self.db = db
        self.plugin_manager = plugin_manager or PluginManager()
        self.network_manager = network_manager
        self.protocol = None
        self.should_reconnect = True

        # Connection retry tracking
        self.current_address = config.primary_address
        self.current_port = config.primary_port
        self.retry_delay = 5.0  # Initial retry delay in seconds
        self.max_retry_delay = 300.0  # Maximum retry delay (5 minutes)
        self.retry_count = 0

    def buildProtocol(self, addr):
        proto = self.protocol_class()
        proto.factory = self
        proto.nickname = self.config.primary_nickname
        proto.username = self.config.ident
        proto.realname = self.config.realname
        proto.db = self.db
        proto.plugin_manager = self.plugin_manager  # Use shared plugin manager

        # Store reference to protocol
        self.protocol = proto
        return proto

    def clientConnectionLost(self, connector, reason):
        Logger.warning(
            f"Connection lost to {self.config.name}: {reason.getErrorMessage()}")

        if self.should_reconnect and self.config.auto_reconnect:
            # Reset retry tracking on successful disconnection after being connected
            # (protocol was created means we had a successful connection)
            if self.protocol is not None:
                self.retry_count = 0
                self.retry_delay = 5.0
                Logger.info(f"Reconnecting to {self.config.name} in {self.retry_delay} seconds...")
              #  connector.connect()
            else:
                # Never successfully connected, rotate to next address/port
                self._rotate.connection_target()
                Logger.info(f"Retrying {self.config.name} with {self.current_address}:{self.current_port} in {self.retry_delay} seconds...")

            # Schedule reconnection with delay
            reactor.callLater(self.retry_delay, connector.connect)
        else:
            Logger.info(f"Not reconnecting to {self.config.name} (reconnect disabled)")

    def clientConnectionFailed(self, connector, reason):
        Logger.error(
            f"Connection failed to {self.config.name} ({self.current_address}:{self.current_port}): {reason.getErrorMessage()}")

        if self.should_reconnect and self.config.auto_reconnect:
            # Rotate to next address/port combination
            self._rotate_connection_target()

            # Increase retry delay with exponential backoff
            self.retry_count += 1
            self.retry_delay = min(self.retry_delay * 1.5, self.max_retry_delay)

            Logger.info(
                f"Retrying connection to {self.config.name} "
                f"({self.current_address}:{self.current_port}) "
                f"in {self.retry_delay:.1f} seconds (attempt #{self.retry_count})..."
            )

            # Schedule reconnection with delay
            reactor.callLater(self.retry_delay, connector.connect)
        else:
            Logger.info(f"Not retrying connection to {self.config.name} (reconnect disabled)")

    def _rotate_connection_target(self):

        # First try next port on current address
        next_port = self.config.get_next_port(self.current_port)

        # If we've cycled through all ports, move to next address
        if next_port == self.config.primary_port or next_port == self.current_port:
            self.current_address = self.config.get_next_address(self.current_address)
            self.current_port = self.config.primary_port
            Logger.debug(f"Rotating to next address: {self.current_address}")
        else:
            self.current_port = next_port
            Logger.debug(f"Rotating to next port: {self.current_port}")

        # Update network manager's tracked address if available
        if self.network_manager:
            self.network_manager.connected_addresses[self.config.id] = (
                self.current_address,
                self.current_port
            )
