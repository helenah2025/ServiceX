"""
Dunamis IRC Bot - Database Manager

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

from typing import Optional, List, Dict, Any
from pathlib import Path
import sqlite3

from .logger import Logger
from .network_config import NetworkConfig


class DatabaseManager:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.connection: Optional[sqlite3.Connection] = None
        self.cursor: Optional[sqlite3.Cursor] = None

    def connect(self) -> bool:
        try:
            self.connection = sqlite3.connect(str(self.db_path))
            self.cursor = self.connection.cursor()
            Logger.info(f"Connected to database: {self.db_path}")
            return True
        except sqlite3.Error as e:
            Logger.error(f"Database connection failed: {e}")
            return False

    def get_networks(self) -> List[NetworkConfig]:
        self.cursor.execute('SELECT * FROM irc_networks')
        networks = []

        for row in self.cursor.fetchall():
            config = NetworkConfig(
                id=row[0],
                name=row[1],
                addresses=row[2].split(', ') if row[2] else [],
                ports=[int(p) for p in row[3].split(', ')] if row[3] else [],
                ssl_ports=[int(p) for p in row[4].split(', ')] if row[4] else [],
                enable_ssl=(row[5] == 1),
                auto_connect=(row[6] == 1),
                auto_reconnect=(row[7] == 1),
                nicknames=row[8].split(', ') if row[8] else [],
                ident=row[9],
                realname=row[10],
                auth_mechanism=row[11],
                sasl_mechanism=row[12],
                auth_username=row[13],
                auth_password=row[14],
                oper_auth=(row[15] == 1),
                oper_username=row[16],
                oper_password=row[17],
                command_prefix=row[18],
                rpl_welcome=row[19],
                rpl_yourhost=row[20],
                rpl_created=row[21],
                rpl_myinfo=row[22],
                rpl_isupport=row[23],
                rpl_visiblehost=row[24]
            )
            networks.append(config)

        return networks

    def add_network(
        self,
        name: str,
        addresses: List[str],
        ports: List[int] = None,
        ssl_ports: List[int] = None,
        enable_ssl: bool = True,
        auto_connect: bool = True,
        auto_reconnect: bool = True,
        nicknames: List[str] = None,
        ident: str = "dunamis",
        realname: str = "Dunamis IRC Bot",
        auth_mechanism: int = 1,
        sasl_mechanism: int = 1,
        auth_username: str = "",
        auth_password: str = "",
        oper_auth: bool = False,
        oper_username: str = "",
        oper_password: str = "",
        command_prefix: str = "!"
    ) -> int:
        try:
            if nicknames is None:
                nicknames = ["Dunamis", "Dunamis_", "Dunamis__"]
            if ports is None:
                ports = [6667]
            if ssl_ports is None:
                ssl_ports = [6697]

            self.cursor.execute(
                '''INSERT INTO irc_networks
                   (name, addresses, ports, ssl_ports, enable_ssl, auto_connect,
                    auto_reconnect, nicknames, ident, realname, auth_mechanism,
                    sasl_mechanism, auth_username, auth_password, oper_auth,
                    oper_username, oper_password, command_prefix)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (name, ', '.join(addresses), ', '.join(map(str, ports)),
                 ', '.join(map(str, ssl_ports)), 1 if enable_ssl else 0,
                 1 if auto_connect else 0, 1 if auto_reconnect else 0,
                 ', '.join(nicknames), ident, realname, auth_mechanism,
                 sasl_mechanism, auth_username, auth_password,
                 1 if oper_auth else 0, oper_username, oper_password,
                 command_prefix)
            )
            self.connection.commit()

            network_id = self.cursor.lastrowid
            Logger.info(f"Added network '{name}' with ID {network_id}")
            return network_id

        except sqlite3.Error as e:
            Logger.error(f"Failed to add network: {e}")
            raise

    def remove_network(self, network_id: int) -> bool:
        try:
            # Remove associated channels
            self.cursor.execute(
                'DELETE FROM irc_channels WHERE network_id=?',
                (network_id,)
            )

            # Remove associated plugin states
            self.cursor.execute(
                'DELETE FROM plugins_state WHERE network_id=?',
                (network_id,)
            )

            # Remove associated tasks
            self.cursor.execute(
                'DELETE FROM tasks WHERE from_network_id=? OR for_network_id=?',
                (network_id, network_id)
            )

            # Remove the network
            self.cursor.execute(
                'DELETE FROM irc_networks WHERE id=?',
                (network_id,)
            )

            rows_affected = self.cursor.rowcount
            self.connection.commit()

            if rows_affected > 0:
                Logger.info(f"Removed network ID {network_id}")
                return True
            else:
                Logger.warning(f"Network ID {network_id} not found")
                return False

        except sqlite3.Error as e:
            Logger.error(f"Failed to remove network: {e}")
            return False

    def update_network(self, network_id: int, updates: Dict[str, Any]) -> bool:
        try:
            set_clauses = []
            values = []

            for key, value in updates.items():
                # Convert lists to comma-separated strings
                if key in ['addresses', 'nicknames'] and isinstance(value, list):
                    value = ', '.join(value)
                elif key in ['ports', 'ssl_ports'] and isinstance(value, list):
                    value = ', '.join(map(str, value))
                # Convert booleans to integers
                elif key in ['enable_ssl', 'auto_connect', 'auto_reconnect', 'oper_auth']:
                    value = 1 if value else 0

                set_clauses.append(f"{key}=?")
                values.append(value)

            if not set_clauses:
                return False

            values.append(network_id)
            query = f"UPDATE irc_networks SET {', '.join(set_clauses)} WHERE id=?"

            self.cursor.execute(query, values)
            rows_affected = self.cursor.rowcount
            self.connection.commit()

            if rows_affected > 0:
                Logger.info(f"Updated network ID {network_id}")
                return True
            else:
                Logger.warning(f"Network ID {network_id} not found")
                return False

        except sqlite3.Error as e:
            Logger.error(f"Failed to update network: {e}")
            return False

    def update_network_rpl(self, network_id: int, rpl_type: str, value: str) -> bool:
        try:
            valid_types = ['rpl_welcome', 'rpl_yourhost', 'rpl_created', 
                          'rpl_myinfo', 'rpl_isupport', 'rpl_visiblehost']

            if rpl_type not in valid_types:
                Logger.error(f"Invalid RPL type: {rpl_type}")
                return False

            query = f"UPDATE irc_networks SET {rpl_type}=? WHERE id=?"
            self.cursor.execute(query, (value, network_id))
            self.connection.commit()

            return True
        except sqlite3.Error as e:
            Logger.error(f"Failed to update RPL data: {e}")
            return False

    def get_channels(self, network_id: int) -> List[Dict[str, Any]]:
        self.cursor.execute(
            'SELECT * FROM irc_channels WHERE network_id=?',
            (network_id,)
        )
        channels = []
        for row in self.cursor.fetchall():
            channels.append({
                'id': row[0],
                'network_id': row[1],
                'name': row[2],
                'password': row[3],
                'auto_join': row[4] == 1,
                'auto_rejoin': row[5] == 1,
                'enable_logging': row[6] == 1,
                'command_prefix': row[7],
                'last_topic': row[8],
                'last_modes': row[9]
            })
        return channels

    def get_auto_join_channels(self, network_id: int) -> List[str]:
        self.cursor.execute(
            'SELECT name FROM irc_channels WHERE network_id=? AND auto_join=1',
            (network_id,)
        )
        return [row[0] for row in self.cursor.fetchall()]

    def get_channel_by_name(self, network_id: int, channel_name: str) -> Optional[Dict[str, Any]]:
        """Get channel info by network ID and channel name"""
        try:
            self.cursor.execute(
                'SELECT * FROM irc_channels WHERE network_id=? AND name=?',
                (network_id, channel_name)
            )
            row = self.cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'network_id': row[1],
                    'name': row[2],
                    'password': row[3],
                    'auto_join': row[4] == 1,
                    'auto_rejoin': row[5] == 1,
                    'enable_logging': row[6] == 1,
                    'command_prefix': row[7],
                    'last_topic': row[8],
                    'last_modes': row[9]
                }
            return None
        except sqlite3.Error as e:
            Logger.error(f"Failed to get channel: {e}")
            return None

    def add_channel(self, network_id: int, channel_name: str,
                   password: str = "", auto_join: bool = True,
                   auto_rejoin: bool = False, enable_logging: bool = True,
                   command_prefix: str = None) -> bool:
        try:
            self.cursor.execute(
                '''INSERT INTO irc_channels
                   (network_id, name, password, auto_join, auto_rejoin,
                    enable_logging, command_prefix)
                   VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (network_id, channel_name, password, 1 if auto_join else 0,
                 1 if auto_rejoin else 0, 1 if enable_logging else 0,
                 command_prefix)
            )
            self.connection.commit()
            Logger.info(f"Success: added channel name '{channel_name}' to database")
            return True
        except sqlite3.IntegrityError:
            Logger.warning(f"Channel '{channel_name}' already exists on network {network_id}")
            return False

    def remove_channel(self, network_id: int, channel_id: int) -> bool:
        try:
            self.cursor.execute(
                'DELETE FROM irc_channels WHERE id=? AND network_id=?',
                (channel_id, network_id)
            )
            rows_affected = self.cursor.rowcount
            self.connection.commit()

            if rows_affected > 0:
                Logger.info(f"Success: removed channel ID '{channel_id}' from database")
                return True
            else:
                Logger.warning(f"Channel ID '{channel_id}' not found")
                return False
        except sqlite3.Error as e:
            Logger.error(f"Failed to remove channel: {e}")
            return False

    def update_channel(self, network_id: int, channel_name: str,
                      updates: Dict[str, Any]) -> bool:
        try:
            set_clauses = []
            values = []

            for key, value in updates.items():
                if key in ['auto_join', 'auto_rejoin', 'enable_logging']:
                    value = 1 if value else 0
                set_clauses.append(f"{key}=?")
                values.append(value)

            if not set_clauses:
                return False

            values.extend([channel_name, network_id])
            query = f"UPDATE irc_channels SET {', '.join(set_clauses)} WHERE name=? AND network_id=?"

            self.cursor.execute(query, values)
            rows_affected = self.cursor.rowcount
            self.connection.commit()

            return rows_affected > 0

        except sqlite3.Error as e:
            Logger.error(f"Failed to update channel: {e}")
            return False

    def get_plugins(self) -> List[Dict[str, Any]]:
        self.cursor.execute('SELECT * FROM plugins')
        plugins = []
        for row in self.cursor.fetchall():
            plugins.append({
                'id': row[0],
                'name': row[1],
                'enable_global': row[2] == 1
            })
        return plugins

    def add_plugin(self, name: str, enable_global: bool = True) -> int:
        try:
            self.cursor.execute(
                'INSERT INTO plugins (name, enable_global) VALUES (?, ?)',
                (name, 1 if enable_global else 0)
            )
            self.connection.commit()
            return self.cursor.lastrowid
        except sqlite3.IntegrityError:
            Logger.info(f"Plugin {name} already in registry")
            return -1

    def get_plugin_states(self, network_id: int = None,
                         target: str = None) -> List[Dict[str, Any]]:
        query = 'SELECT * FROM plugins_state WHERE 1=1'
        params = []

        if network_id is not None:
            query += ' AND network_id=?'
            params.append(network_id)

        if target is not None:
            query += ' AND target=?'
            params.append(target)

        self.cursor.execute(query, params)
        states = []
        for row in self.cursor.fetchall():
            states.append({
                'id': row[0],
                'plugin_id': row[1],
                'network_id': row[2],
                'target': row[3],
                'enable': row[4] == 1
            })
        return states

    def update_plugin_state(self, plugin_id: int, network_id: int,
                          target: str, enable: bool):
        try:
            # Check if state exists
            self.cursor.execute(
                '''SELECT id FROM plugins_state
                   WHERE plugin_id=? AND network_id=? AND target=?''',
                (plugin_id, network_id, target)
            )
            existing = self.cursor.fetchone()

            if existing:
                self.cursor.execute(
                    '''UPDATE plugins_state SET enable=?
                       WHERE plugin_id=? AND network_id=? AND target=?''',
                    (1 if enable else 0, plugin_id, network_id, target)
                )
            else:
                self.cursor.execute(
                    '''INSERT INTO plugins_state
                       (plugin_id, network_id, target, enable)
                       VALUES (?, ?, ?, ?)''',
                    (plugin_id, network_id, target, 1 if enable else 0)
                )

            self.connection.commit()
        except sqlite3.Error as e:
            Logger.error(f"Failed to update plugin state: {e}")

    def get_tasks(self, network_id: int = None,
                  persistent_only: bool = False) -> List[Dict[str, Any]]:
        query = 'SELECT * FROM tasks WHERE 1=1'
        params = []

        if network_id is not None:
            query += ' AND (from_network_id=? OR for_network_id=?)'
            params.extend([network_id, network_id])

        if persistent_only:
            query += ' AND persistent=1'

        self.cursor.execute(query, params)
        tasks = []
        for row in self.cursor.fetchall():
            tasks.append({
                'id': row[0],
                'plugin_id': row[1],
                'from_network_id': row[2],
                'from_target': row[3],
                'for_network_id': row[4],
                'for_target': row[5],
                'name': row[6],
                'callback': row[7],
                'interval': row[8],
                'periodic': row[9] == 1,
                'delay': row[10],
                'max_runs': row[11],
                'description': row[12],
                'auto_start': row[13] == 1,
                'state': row[14],
                'persistent': row[15] == 1
            })
        return tasks

    def add_task(self, plugin_id: int, from_network_id: int, from_target: str,
                for_network_id: int, for_target: str, name: str, callback: str,
                interval: float = None, periodic: bool = True, delay: float = 0.0,
                max_runs: int = 0, description: str = "", auto_start: bool = False,
                state: str = "PENDING", persistent: bool = False) -> int:
        try:
            self.cursor.execute(
                '''INSERT INTO tasks
                   (plugin_id, from_network_id, from_target, for_network_id,
                    for_target, name, callback, interval, periodic, delay,
                    max_runs, description, auto_start, state, persistent)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (plugin_id, from_network_id, from_target, for_network_id,
                 for_target, name, callback, interval, 1 if periodic else 0,
                 delay, max_runs, description, 1 if auto_start else 0,
                 state, 1 if persistent else 0)
            )
            self.connection.commit()
            return self.cursor.lastrowid
        except sqlite3.Error as e:
            Logger.error(f"Failed to add task: {e}")
            return -1

    def update_task(self, task_id: int, updates: Dict[str, Any]) -> bool:
        try:
            set_clauses = []
            values = []

            for key, value in updates.items():
                if key in ['periodic', 'auto_start', 'persistent']:
                    value = 1 if value else 0
                set_clauses.append(f"{key}=?")
                values.append(value)

            if not set_clauses:
                return False

            values.append(task_id)
            query = f"UPDATE tasks SET {', '.join(set_clauses)} WHERE id=?"

            self.cursor.execute(query, values)
            rows_affected = self.cursor.rowcount
            self.connection.commit()

            return rows_affected > 0

        except sqlite3.Error as e:
            Logger.error(f"Failed to update task: {e}")
            return False

    def remove_task(self, task_id: int) -> bool:
        try:
            self.cursor.execute('DELETE FROM tasks WHERE id=?', (task_id,))
            rows_affected = self.cursor.rowcount
            self.connection.commit()
            return rows_affected > 0
        except sqlite3.Error as e:
            Logger.error(f"Failed to remove task: {e}")
            return False
