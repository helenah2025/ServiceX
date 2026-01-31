"""
Dunamis IRC Bot - Protocol

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

from typing import Optional, List
import shlex
import base64

from twisted.words.protocols import irc

from .logger import Logger
from .plugin_manager import PluginManager
from .task_scheduler import TaskScheduler
from .database_manager import DatabaseManager


class Protocol(irc.IRCClient):
    versionName = "Dunamis"
    versionNum = "3.0"
    versionEnv = "Python/Twisted"

    def __init__(self):
        super().__init__()
        self.plugin_manager: Optional[PluginManager] = None
        self.scheduler = TaskScheduler()
        self.db: Optional[DatabaseManager] = None
        self.joined_channels: List[str] = []
        self.sasl_authenticated = False

    def connectionMade(self):
        # Handle SASL if needed
        config = self.factory.config
        if config.auth_mechanism == 1:  # SASL
            if config.sasl_mechanism == 1:  # PLAIN
                self.sendLine('CAP REQ :sasl')
            elif config.sasl_mechanism == 2:  # EXTERNAL
                self.sendLine('CAP REQ :sasl')

        irc.IRCClient.connectionMade(self)
        Logger.info(
            f"Connected to IRC network: {config.name}"
        )

        # Load enabled plugins
        plugins = self.db.get_plugins()
        for plugin in plugins:
            if plugin['enable_global']:
                if plugin['name'] not in self.plugin_manager.loaded_plugins:
                    self.plugin_manager.load_plugin(plugin['name'])

        # Load persistent tasks
        self._load_persistent_tasks()

    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)
        Logger.warning(
            f"Connection lost to {self.factory.config.name}: {reason.getErrorMessage()}"
        )
        self.scheduler.stop_all_tasks()

    def irc_CAP(self, prefix, params):
        if params[1] == 'ACK' and 'sasl' in params[2]:
            config = self.factory.config
            if config.sasl_mechanism == 1:  # PLAIN
                self.sendLine('AUTHENTICATE PLAIN')
            elif config.sasl_mechanism == 2:  # EXTERNAL
                self.sendLine('AUTHENTICATE EXTERNAL')

    def irc_AUTHENTICATE(self, prefix, params):
        if params[0] == '+':
            config = self.factory.config
            if config.sasl_mechanism == 1:  # PLAIN
                auth_string = f"{config.auth_username}\x00{config.auth_username}\x00{config.auth_password}"
                auth_bytes = auth_string.encode('utf-8')
                auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
                self.sendLine(f'AUTHENTICATE {auth_b64}')

    def irc_903(self, prefix, params):
        self.sasl_authenticated = True
        Logger.info("SASL authentication successful")
        self.sendLine('CAP END')

    def irc_904(self, prefix, params):
        Logger.error("SASL authentication failed")
        self.sendLine('CAP END')

    def irc_001(self, prefix, params):
        welcome_msg = params[1] if len(params) > 1 else ""
        self.db.update_network_rpl(self.factory.config.id, 'rpl_welcome', welcome_msg)
        Logger.info(f"RPL_WELCOME: {welcome_msg}")

    def irc_002(self, prefix, params):
        yourhost_msg = params[1] if len(params) > 1 else ""
        self.db.update_network_rpl(self.factory.config.id, 'rpl_yourhost', yourhost_msg)

    def irc_003(self, prefix, params):
        created_msg = params[1] if len(params) > 1 else ""
        self.db.update_network_rpl(self.factory.config.id, 'rpl_created', created_msg)

    def irc_004(self, prefix, params):
        myinfo_msg = ' '.join(params[1:]) if len(params) > 1 else ""
        self.db.update_network_rpl(self.factory.config.id, 'rpl_myinfo', myinfo_msg)

    def irc_005(self, prefix, params):
        isupport_msg = ' '.join(params[1:]) if len(params) > 1 else ""
        self.db.update_network_rpl(self.factory.config.id, 'rpl_isupport', isupport_msg)

    def irc_396(self, prefix, params):
        visiblehost_msg = params[1] if len(params) > 1 else ""
        self.db.update_network_rpl(self.factory.config.id, 'rpl_visiblehost', visiblehost_msg)

    def signedOn(self):
        config = self.factory.config

        # Handle non-SASL authentication
        if config.auth_mechanism == 2:  # NickServ
            Logger.info(f"Identifying with NickServ as {config.auth_username}")
            self.msg('NickServ', f'IDENTIFY {config.auth_username} {config.auth_password}')
        elif config.auth_mechanism == 3:  # Custom command
            # Could be implemented with a custom command from config
            pass

        # Oper authentication
        if config.oper_auth:
            Logger.info(f"Authenticating as oper: {config.oper_username}")
            self.sendLine(f'OPER {config.oper_username} {config.oper_password}')

        # Join auto-join channels
        all_channels = self.db.get_channels(config.id)
        for channel in all_channels:
            if channel['auto_join']:
                Logger.info(f"[{self.factory.config.name}] Auto-joining channel ID {channel['id']}: {channel['name']}")
                self.join_channel(channel['id'], save_to_db=False)

    def alterCollidedNick(self, nickname: str) -> str:
        next_nick = self.factory.config.get_next_nickname(nickname)
        Logger.info(f"Nickname {nickname} taken, trying {next_nick}")
        return next_nick

    def joined(self, channel: str):
        Logger.info(f"[{self.factory.config.name}] Joined channel: {channel}")
        if channel not in self.joined_channels:
            self.joined_channels.append(channel)

    def left(self, channel: str):
        Logger.info(f"[{self.factory.config.name}] Left channel: {channel}")
        if channel in self.joined_channels:
            self.joined_channels.remove(channel)

    def kickedFrom(self, channel: str, kicker: str, message: str):
        Logger.warning(f"Kicked from {channel} by {kicker}: {message}")

        # Check if auto-rejoin is enabled
        channel_info = self.db.get_channels(self.factory.config.id)
        for ch in channel_info:
            if ch['name'] == channel and ch['auto_rejoin']:
                Logger.info(f"Auto-rejoining {channel}")
                self.join_channel(channel, save_to_db=False)
                break

    def topicUpdated(self, user: str, channel: str, newTopic: str):
        self.db.update_channel(
            self.factory.config.id,
            channel,
            {'last_topic': newTopic}
        )

    def modeChanged(self, user: str, channel: str, set: bool, modes: str, args: tuple):
        mode_str = ('+' if set else '-') + modes
        if args:
            # Filter out None values and convert to strings
            str_args = [str(arg) for arg in args if arg is not None]
            if str_args:
                mode_str += ' ' + ' '.join(str_args)

        self.db.update_channel(
            self.factory.config.id,
            channel,
            {'last_modes': mode_str}
        )

    def join_channel(self, channel_id: int, save_to_db: bool = True):
        # Look up channel by ID
        channel_info = None
        channels = self.db.get_channels(self.factory.config.id)

        for ch in channels:
            if ch['id'] == channel_id:
                channel_info = ch
                break

        if not channel_info:
            Logger.error(f"Channel ID '{channel_id}' not found in database")
            return

        channel_name = channel_info['name']

        if channel_name in self.joined_channels:
            Logger.info(f"Already in channel '{channel_name}'")
            return

        # Use password from database
        password = channel_info.get('password', '')

        if password:
            self.join(channel_name, password)
        else:
            self.join(channel_name)

    def join_channel_by_name(self, channel_name: str, save_to_db: bool = True, password: str = ""):
        if not channel_name:
            return

        channel_name = channel_name.split()[0]

        if channel_name in self.joined_channels:
            Logger.info(f"Already in channel: {channel_name}")
            return

        # Check if channel exists in database
        channel_info = self.db.get_channel_by_name(self.factory.config.id, channel_name)

        if not channel_info and not save_to_db:
            Logger.warning(f"Cannot join {channel_name}: not in database")
            return

        Logger.info(f"[{self.factory.config.name}] Joining channel: {channel_name}")

        # Use password from database if available and not provided
        if channel_info and not password:
            password = channel_info.get('password', '')

        if password:
            self.join(channel_name, password)
        else:
            self.join(channel_name)

        if save_to_db:
            if not self.db.add_channel(self.factory.config.id, channel_name, password=password):
                Logger.error(f"Failed to add channel {channel_name} to database (may already exist)")

    def part_channel(self, channel_id: int, save_to_db: bool = True):
        # Look up channel by ID
        channel_info = None
        channels = self.db.get_channels(self.factory.config.id)

        for ch in channels:
            if ch['id'] == channel_id:
                channel_info = ch
                break

        if not channel_info:
            Logger.error(f"Channel ID '{channel_id}' not found in database")
            return

        channel_name = channel_info['name']

        if channel_name not in self.joined_channels:
            Logger.info(f"Not in channel: '{channel_name}'")
            return

        Logger.info(f"[{self.factory.config.name}] Parting channel: {channel_name} (ID: {channel_id})")
        self.leave(channel_name)

    def send_message(self, target: str, message: str,
                     prefix_nick: Optional[str] = None):
        if prefix_nick:
            message = f"{prefix_nick}: {message}"

        for line in message.split('\n'):
            self.msg(target, line)

    def privmsg(self, user: str, channel: str, message: str):
        try:
            nickname, user_info = user.split('!')
            ident, hostname = user_info.split('@')
        except ValueError:
            return

        message = message.strip()
        if not message:
            return

        is_pm = (channel == self.nickname)
        target = nickname if is_pm else channel

        # Get command prefix (channel-specific or network default)
        prefix = self.factory.config.command_prefix

        if not is_pm:
            channels = self.db.get_channels(self.factory.config.id)
            for ch in channels:
                if ch['name'] == channel and ch['command_prefix']:
                    prefix = ch['command_prefix']
                    break

        if is_pm or message.startswith(prefix):
            self._handle_command(target, nickname, message, is_pm, prefix)

    def _handle_command(
            self,
            target: str,
            nickname: str,
            message: str,
            is_pm: bool,
            prefix: str):

        if not is_pm:
            message = message[len(prefix):]

        try:
            parts = shlex.split(message)
        except ValueError as e:
            if "closing quotation" in str(e).lower():
                self.send_message(
                    target, "Missing closing quotation mark", nickname)
            return

        if not parts:
            return

        command = parts[0]
        args = parts[1:]

        success = self.plugin_manager.execute_command(
            command, self, target, nickname, args
        )

        if not success:
            Logger.info(f"Unknown command '{command}' from {nickname}")
            self.send_message(target, "Command not found", nickname)
        else:
            Logger.info(
                f"[{self.factory.config.name}] Executed command '{command}' from {nickname}")

    def noticed(self, user: str, channel: str, message: str):
        if user.startswith("NickServ!"):
            if "Password accepted" in message or "identified" in message.lower():
                Logger.info("Successfully identified with NickServ")
            elif "isn't registered" in message or "incorrect" in message.lower():
                Logger.error("Failed to identify with NickServ")

    def _load_persistent_tasks(self):
        tasks = self.db.get_tasks(
            network_id=self.factory.config.id,
            persistent_only=True
        )

        for task_data in tasks:
            if task_data['state'] in ['RUNNING', 'PAUSED']:
                # TODO: Reconstruct task from database
                # This would require serializing/deserializing callbacks
                Logger.info(f"Found persistent task: {task_data['name']}")
