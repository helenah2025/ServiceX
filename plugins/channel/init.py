"""
Channel Plugin for Dunamis
Provides IRC channel management commands

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

from typing import List
from getopt import getopt, GetoptError


PLUGIN_INFO = {
    "name": "Channel",
    "author": "Helenah, Helena Bolan",
    "version": "2.0",
    "description": "IRC channel management and information commands"
}


def format_channel_list(channels: List[str]) -> str:
    if not channels:
        return "I am not in any channels on this IRC network."

    if len(channels) == 1:
        return f"I am just in {channels[0]} on this IRC network."

    # Multiple channels
    all_but_last = ", ".join(channels[:-1])
    last_channel = channels[-1]
    total = len(channels)

    return (
        f"I am in {all_but_last} and {last_channel} on this IRC network, "
        f"a total of {total} channel{'s' if total != 1 else ''}."
    )


def command_channel(bot, target: str, nickname: str, args: List[str]):
    handlers = {
        "join": handle_join,
        "part": handle_part,
        "cycle": handle_cycle,
        "list": handle_list,
        "info": handle_info,
        "add": handle_add,
        "remove": handle_remove,
        "modify": handle_modify,
    }

    subcommand_list = ", ".join(handlers.keys())

    if not args:
        bot.send_message(target, f"Usage: requires a subcommand: {subcommand_list}", nickname)
        return

    subcommand = args[0].lower()
    subargs = args[1:]

    handler = handlers.get(subcommand)

    if handler:
        handler(bot, target, nickname, subargs)
    else:
        bot.send_message(target, f"Error: unknown subcommand: {subcommand} - available subcommands: {subcommand_list}", nickname)


def handle_join(bot, target: str, nickname: str, args: List[str]):
    usage = "Usage: channel join <channel_id>"
    if not args:
        bot.send_message(target, usage, nickname)
        return

    try:
        channel_id = int(args[0])
    except ValueError:
        bot.send_message(target, usage, nickname)
        return

    # Join the channel
    bot.join_channel(channel_id, save_to_db=False)
    bot.send_message(target, f"Success: joining channel ID '{channel_id}'", nickname)


def handle_part(bot, target: str, nickname: str, args: List[str]):
    usage = "Usage: channel part <channel_id>"
    if not args:
        bot.send_message(target, usage, nickname)
        return

    try:
        channel_id = int(args[0])
    except ValueError:
        bot.send_message(target, usage, nickname)
        return

    # Part the channel
    bot.part_channel(channel_id, save_to_db=False)
    bot.send_message(target, f"Success: joining channel ID '{channel_id}'", nickname)


def handle_cycle(bot, target: str, nickname: str, args: List[str]):
    if args:
        try:
            channel_id = int(args[0])
        except ValueError:
            bot.send_message(target, "Usage: channel cycle <channel_id>", nickname)
            return

    # Find the channel
    all_networks = bot.db.get_networks()
    channel_info = None
    network_id = None

    for network in all_networks:
        channels = bot.db.get_channels(network.id)
        for ch in channels:
            if ch['id'] == channel_id and ch['network_id'] == network.id:
                channel_info = ch
                network_id = network.id
                break
        if channel_info:
            break

    if not channel_info:
        bot.send_message(target, f"Error channel ID '{channel_id}' not found in database", nickname)
        return

    bot.send_message(target, f"Success: channel ID '{channel_id}' cycled", nickname)
    bot.part_channel(channel_id, save_to_db=False)
    bot.join_channel(channel_id, save_to_db=False)


def handle_list(bot, target: str, nickname: str, args: List[str]):
    # Show all channels from database across all networks
    network_manager = None
    if hasattr(bot, 'factory') and hasattr(bot.factory, 'network_manager'):
        network_manager = bot.factory.network_manager

    # Get all networks
    all_networks = bot.db.get_networks()

    if not all_networks:
        bot.send_message(target, "No networks configured", nickname)
        return

    all_channels = []
    for network in all_networks:
        channels = bot.db.get_channels(network.id)
        for ch in channels:
            # Check if currently joined
            is_joined = False
            if network_manager:
                protocol = network_manager.get_protocol(network.id)
                if protocol and hasattr(protocol, 'joined_channels'):
                    is_joined = ch['name'] in protocol.joined_channels

            all_channels.append({
                'id': ch['id'],
                'name': ch['name'],
                'network_id': network.id,
                'network_name': network.name,
                'joined': is_joined,
                'auto_join': ch['auto_join'],
                'auto_rejoin': ch['auto_rejoin'],
                'logging': ch['enable_logging']
            })

    if not all_channels:
        bot.send_message(target, "No channels configured in database", nickname)
        return

    # Format output
    parts = []
    for ch in all_channels:
        status = "Joined" if ch['joined'] else "Not joined"
        parts.append({
            'id': ch['id'],
            'name': ch['name'],
            'network_id': ch['network_id'],
            'network_name': ch['network_name'],
            'status': status
        })

    parts_sorted = sorted(parts, key=lambda part: part['id'])
    formatted_parts = []

    for part in parts_sorted:
        formatted_parts.extend([
            f"[ ID: {part['id']}, "
            f"Name: {part['name']}, "
            f"Network ID: {part['network_id']}, "
            f"Status: {part['status']} ]"
        ])

    bot.send_message(target, " -- ".join(formatted_parts), nickname)


def handle_info(bot, target: str, nickname: str, args: List[str]):
    if not args:
        bot.send_message(target, "Usage: channel info <channel_id>", nickname)
        return

    try:
        channel_id = int(args[0])
    except ValueError:
        bot.send_message(
            target,
            f"Error: invalid channel ID: {args[0]}",
            nickname)
        return

    # Get all networks
    all_networks = bot.db.get_networks()

    # Search across all networks for the channel ID
    channel_info = None
    network_info = None

    for network in all_networks:
        channels = bot.db.get_channels(network.id)
        for ch in channels:
            if ch['id'] == channel_id:
                channel_info = ch
                network_info = network
                break
        if channel_info:
            break

    if not channel_info:
        bot.send_message(
            target,
            f"Error: channel ID {channel_id} not found in database",
            nickname)
        return

    channel_name = channel_info['name']

    # Check if bot is currently in the channel
    status = "Unknown"
    if network_info.id == bot.factory.config.id:
        if channel_name in bot.joined_channels:
            status = "Joined"
        else:
            status = "Not joined"
    else:
        # Check if the network is connected
        network_manager = None
        if hasattr(bot, 'factory') and hasattr(bot.factory, 'network_manager'):
            network_manager = bot.factory.network_manager

        if network_manager:
            protocol = network_manager.get_protocol(network_info.id)
            if protocol and hasattr(protocol, 'joined_channels'):
                if channel_name in protocol.joined_channels:
                    status = "Joined"
                else:
                    status = "Not joined"
            else:
                status = "Network not connected"

    parts = [
        f"ID: {channel_info['id']}",
        f"Name: {channel_name}",
        f"Network ID: {network_info.id}",
        f"Status: {status}",
        f"Auto-Join: {'Yes' if channel_info['auto_join'] else 'No'}",
        f"Auto-Rejoin: {'Yes' if channel_info['auto_rejoin'] else 'No'}",
        f"Logging: {'Yes' if channel_info['enable_logging'] else 'No'}",
    ]

    # Add optional fields if they exist
    if channel_info.get('command_prefix'):
        parts.append(f"Command Prefix: {channel_info['command_prefix']}")
    if channel_info.get('last_topic'):
        parts.append(f"Last Topic: {channel_info['last_topic']}")
    if channel_info.get('last_modes'):
        parts.append(f"Last Modes: {channel_info['last_modes']}")

    bot.send_message(target, ", ".join(parts), nickname)


def handle_add(bot, target: str, nickname: str, args: List[str]):
    if args:
        channel_name = args[0]
        args = args[1:]
    else:
        bot.send_message(target, "Usage: channel add <channel_name> <flags>", nickname)
        return

    # Parse options
    network_id = None
    password = ""
    auto_join = True
    auto_rejoin = False
    enable_logging = True
    command_prefix = None

    try:
        opts, remaining = getopt(
            args,
            "n:p:",
            [
                "network=", "password=",
                "auto-join=", "auto-rejoin=",
                "logging=", "prefix="
            ]
        )

        for opt, arg in opts:
            if opt in ("-n", "--network"):
                network_id = int(arg)
            elif opt in ("-p", "--password"):
                password = arg
            elif opt == "--auto-join":
                auto_join = arg.lower() in ['true', 'yes', '1']
            elif opt == "--auto-rejoin":
                auto_rejoin = arg.lower() in ['true', 'yes', '1']
            elif opt == "--logging":
                enable_logging = arg.lower() in ['true', 'yes', '1']
            elif opt == "--prefix":
                command_prefix = arg

    except GetoptError as e:
        bot.send_message(target, f"Error: invalid option: {e}", nickname)
        return
    except ValueError as e:
        bot.send_message(target, f"Error: invalid value: {e}", nickname)
        return

    # Validate required fields
    if not channel_name:
        bot.send_message(target, "Error: channel name required (-c CHANNEL)", nickname)
        return

    if not channel_name.startswith('#'):
        bot.send_message(target, f"Error: invalid channel name: {channel_name}", nickname)
        return

    # Default to current network if not specified
    if network_id is None:
        network_id = bot.factory.config.id

    # Add channel to database
    if bot.db.add_channel(
        network_id=network_id,
        channel_name=channel_name,
        password=password,
        auto_join=auto_join,
        auto_rejoin=auto_rejoin,
        enable_logging=enable_logging,
        command_prefix=command_prefix
    ):
        bot.send_message(
            target,
            f"Success: channel '{channel_name}' added to database under network ID '{network_id}'",
            nickname
        )
    else:
        bot.send_message(
            target,
            f"Error: channel '{channel_name}' already exists in database under network ID '{network_id}'",
            nickname
        )


def handle_remove(bot, target: str, nickname: str, args: List[str]):
    if not args:
        bot.send_message(target, "Usage: channel remove <channel_id>", nickname)
        return

    try:
        channel_id = int(args[0])
    except ValueError:
        bot.send_message(target, f"Error: invalid channel ID: {args[0]}", nickname)
        return

    # Find the channel
    all_networks = bot.db.get_networks()
    channel_info = None
    network_info = None

    for network in all_networks:
        channels = bot.db.get_channels(network.id)
        for ch in channels:
            if ch['id'] == channel_id:
                channel_info = ch
                network_info = network
                break
        if channel_info:
            break

    if not channel_info:
        bot.send_message(target, f"Error: channel ID '{channel_id}' not found in database", nickname)
        return

    channel_name = channel_info['name']

    # Remove from database
    if bot.db.remove_channel(network_info.id, channel_id):
        bot.send_message(
            target,
            f"Success: channel ID '{channel_id}' removed from database",
            nickname
        )

        # If this is the current network and bot is in the channel, part it
        if network_info.id == bot.factory.config.id and channel_name in bot.joined_channels:
            bot.send_message(target, f"Parting channel {channel_name} (removed from database)", nickname)
            bot.leave(channel_name)
        # If it's a different network but connected, part it there
        elif hasattr(bot, 'factory') and hasattr(bot.factory, 'network_manager'):
            network_manager = bot.factory.network_manager
            protocol = network_manager.get_protocol(network_info.id)
            if protocol and hasattr(protocol, 'joined_channels'):
                if channel_name in protocol.joined_channels:
                    protocol.leave(channel_name)
    else:
        bot.send_message(target, f"Error: failed to remove channel from database", nickname)


def handle_modify(bot, target: str, nickname: str, args: List[str]):
    if not args:
        bot.send_message(target, "Usage: channel modify <channel_id> [OPTIONS]", nickname)
        return

    try:
        channel_id = int(args[0])
    except ValueError:
        bot.send_message(target, f"Error: invalid channel ID: {args[0]}", nickname)
        return

    remaining_args = args[1:]

    if not remaining_args:
        bot.send_message(target, "Error: no modifications specified", nickname)
        return

    # Find the channel
    all_networks = bot.db.get_networks()
    channel_info = None
    network_info = None

    for network in all_networks:
        channels = bot.db.get_channels(network.id)
        for ch in channels:
            if ch['id'] == channel_id:
                channel_info = ch
                network_info = network
                break
        if channel_info:
            break

    if not channel_info:
        bot.send_message(target, f"Error: channel ID {channel_id} not found", nickname)
        return

    channel_name = channel_info['name']

    # Parse modification options
    updates = {}

    try:
        opts, _ = getopt(
            remaining_args,
            "p:",
            [
                "password=", "auto-join=", "auto-rejoin=",
                "logging=", "prefix="
            ]
        )

        for opt, arg in opts:
            if opt in ("-p", "--password"):
                updates['password'] = arg
            elif opt == "--auto-join":
                updates['auto_join'] = arg.lower() in ('true', 'yes', '1')
            elif opt == "--auto-rejoin":
                updates['auto_rejoin'] = arg.lower() in ('true', 'yes', '1')
            elif opt == "--logging":
                updates['enable_logging'] = arg.lower() in ('true', 'yes', '1')
            elif opt == "--prefix":
                updates['command_prefix'] = arg

    except GetoptError as e:
        bot.send_message(target, f"Error: invalid option: {e}", nickname)
        return

    # Update database
    try:
        if bot.db.update_channel(network_info.id, channel_name, updates):
            bot.send_message(
                target,
                f"Success: modified channel '{channel_name}' (ID: {channel_id})",
                nickname
            )
        else:
            bot.send_message(target, f"Error: failed to update channel", nickname)

    except Exception as e:
        bot.send_message(target, f"Error: failed to modify channel: {e}", nickname)


__all__ = [
    'PLUGIN_INFO',
    'command_channel',
]
