"""
Dunamis IRC Bot
A modular IRC bot built on Twisted with plugin support

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

import signal
from pathlib import Path
from twisted.internet import reactor

from core import (
    Logger,
    DatabaseManager,
    NetworkManager
)


def main():
    # Initialize logging first
    Logger.setup()
    Logger.info("Dunamis starting...")

    # Check database exists
    db_path = Path("dunamis.db")
    if not db_path.exists():
        Logger.error("Database not found. Run 'dunamis-setup' first.")
        return

    # Connect to database
    db = DatabaseManager(db_path)
    if not db.connect():
        Logger.error("Failed to connect to database")
        return

    # Create network manager
    network_manager = NetworkManager(db)

    # Load network configurations
    networks = network_manager.load_networks()

    if not networks:
        Logger.error("No networks configured in database")
        return

    # Setup graceful shutdown
    def shutdown(signum=None, frame=None):
        Logger.info("Shutdown signal received, cleaning up...")
        
        # Disable reconnection for all networks
        for network_id, factory in network_manager.factories.items():
            factory.should_reconnect = False
        
        # Disconnect all networks
        network_manager.disconnect_all()
        
        # Stop the reactor
        if reactor.running:
            reactor.stop()
        
        Logger.info("Dunamis shut down gracefully")

    # Register signal handlers for graceful shutdown
    # Use reactor.addSystemEventTrigger instead of signal handlers
    # This properly integrates with Twisted's event loop
    reactor.addSystemEventTrigger('before', 'shutdown', lambda: shutdown())

    # Connect to all networks
    Logger.info(f"Connecting to {len(networks)} network(s)...")
    network_manager.connect_all()

    # Start reactor
    try:
        reactor.run()
    except KeyboardInterrupt:
        shutdown()

if __name__ == '__main__':
    main()
