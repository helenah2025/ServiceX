"""
Network Plugin for Dunamis
Provides IRC network management commands

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
    "name": "Network",
    "author": "Helenah, Helena Bolan",
    "version": "2.0",
    "description": "IRC network management commands"
}


def get_network_manager(bot):
    if hasattr(bot, 'factory') and hasattr(bot.factory, 'network_manager'):
        return bot.factory.network_manager
    return None


def format_network_info(status: dict) -> str:
    parts = [
        f"ID: {status['id']}",
        f"Name: {status['name']}",
        f"Addresses: {', '.join(status['addresses'])}",
    ]

    # Show both port lists
    if status.get('ports'):
        parts.append(f"Standard Ports: {', '.join(map(str, status['ports']))}")
    if status.get('ssl_ports'):
        parts.append(f"SSL Ports: {', '.join(map(str, status['ssl_ports']))}")

    parts.extend([
        f"SSL: {'Yes' if status['ssl'] else 'No'}",
        f"Auto-connect: {'Yes' if status['auto_connect'] else 'No'}",
        f"Auto-reconnect: {'Yes' if status['auto_reconnect'] else 'No'}",
        f"Connection Status: {'Connected' if status['connected'] else 'Disconnected'}",
    ])

    # Show connected server if connected
    if status.get('connected_address'):
        parts.append(f"Connected to: {status['connected_address']}:{status['connected_port']}")

    # Auth mechanism
    auth_names = {0: "None", 1: "SASL", 2: "NickServ", 3: "Custom"}
    parts.append(f"Authentication Mechanism: {auth_names.get(status['auth_mechanism'], 'Unknown')}")

    if status.get('nickname'):
        parts.append(f"Nickname: {status['nickname']}")

    if status.get('sasl_authenticated'):
        parts.append(f"SASL: Authenticated")

    if status.get('channels'):
        channel_list = ', '.join(status['channels'])
        parts.append(f"Channels: {channel_list}")

    return ', '.join(parts)


def format_network_list(networks: List[dict]) -> str:
    if not networks:
        return "No networks configured"

    parts = []
    for net in networks:
        status = "Connected" if net['connected'] else "Disconnected"
        parts.extend([
            f"[ ID: {net['id']}, "
            f"Name: {net['name']}, "
            f"Status: {status} ]"
        ])

    return ' -- '.join(parts)


def command_network(bot, target: str, nickname: str, args: List[str]):
    network_manager = get_network_manager(bot)

    if network_manager is None:
        bot.send_message(target, "Error: network manager not available", nickname)
        return

    handlers = {
        "list": handle_list,
        "info": handle_info,
        "connect": handle_connect,
        "disconnect": handle_disconnect,
        "reconnect": handle_reconnect,
        "current": handle_current,
        "add": handle_add,
        "remove": handle_remove,
        "modify": handle_modify,
    }

    subcommand_list = ", ".join(handlers.keys())

    if not args:
        bot.send_message(
            target,
            f"Usage: requires a subcommand: {subcommand_list}",
            nickname
        )
        return

    subcommand = args[0].lower()
    subargs = args[1:]

    handler = handlers.get(subcommand)

    if handler:
        handler(bot, target, nickname, subargs)
    else:
        bot.send_message(
            target,
            f"Error: unknown subcommand: {subcommand} - available: {subcommand_list}",
            nickname
        )


def handle_list(bot, target: str, nickname: str, args: List[str]):
    network_manager = get_network_manager(bot)
    networks = network_manager.list_networks()
    output = format_network_list(networks)
    bot.send_message(target, output, nickname)


def handle_info(bot, target: str, nickname: str, args: List[str]):
    network_manager = get_network_manager(bot)

    if not args:
        bot.send_message(target, "Usage: network info NETWORK_ID", nickname)
        return

    try:
        network_id = int(args[0])
    except ValueError:
        bot.send_message(target, f"Error: invalid network ID: {args[0]}", nickname)
        return

    status = network_manager.get_network_status(network_id)

    if status is None:
        bot.send_message(target, f"Error: network not found: {network_id}", nickname)
        return

    output = format_network_info(status)
    bot.send_message(target, output, nickname)


def handle_connect(bot, target: str, nickname: str, args: List[str]):
    network_manager = get_network_manager(bot)

    if not args:
        bot.send_message(target, "Usage: network connect NETWORK_ID", nickname)
        return

    try:
        network_id = int(args[0])
    except ValueError:
        bot.send_message(target, f"Error: invalid network ID: {args[0]}", nickname)
        return

    if network_manager.connect_network(network_id):
        network_name = network_manager.networks[network_id].name
        bot.send_message(
            target,
            f"Success: connecting to network: {network_name}",
            nickname
        )
    else:
        bot.send_message(
            target,
            f"Error: failed to connect to network: {network_id}",
            nickname
        )


def handle_disconnect(bot, target: str, nickname: str, args: List[str]):
    network_manager = get_network_manager(bot)

    if not args:
        bot.send_message(target, "Usage: network disconnect NETWORK_ID", nickname)
        return

    try:
        network_id = int(args[0])
    except ValueError:
        bot.send_message(target, f"Error: invalid network ID: {args[0]}", nickname)
        return

    if network_manager.disconnect_network(network_id):
        network_name = network_manager.networks[network_id].name
        bot.send_message(
            target,
            f"Success: disconnected from network: {network_name}",
            nickname
        )
    else:
        bot.send_message(
            target,
            f"Error: failed to disconnect from network: {network_id}",
            nickname
        )


def handle_reconnect(bot, target: str, nickname: str, args: List[str]):
    network_manager = get_network_manager(bot)

    if not args:
        bot.send_message(target, "Usage: network reconnect NETWORK_ID", nickname)
        return

    try:
        network_id = int(args[0])
    except ValueError:
        bot.send_message(target, f"Error: invalid network ID: {args[0]}", nickname)
        return

    if network_manager.reconnect_network(network_id):
        network_name = network_manager.networks[network_id].name
        bot.send_message(
            target,
            f"Success: reconnecting to network: {network_name}",
            nickname
        )
    else:
        bot.send_message(
            target,
            f"Error: failed to reconnect to network: {network_id}",
            nickname
        )


def handle_current(bot, target: str, nickname: str, args: List[str]):
    network_manager = get_network_manager(bot)
    network_id = bot.factory.config.id
    status = network_manager.get_network_status(network_id)

    if status is None:
        bot.send_message(target, "Error: current network not found", nickname)
        return

    output = format_network_info(status)
    bot.send_message(target, output, nickname)


def handle_add(bot, target: str, nickname: str, args: List[str]):
    if args:
        network_name = args[0]
        args = args[1:]
    else:
        bot.send_message(target, "Usage: network add <network_name> <flags>", nickname)
        return

    network_manager = get_network_manager(bot)

    # Parse options
    addresses = None
    ports = None
    ssl_ports = None
    enable_ssl = True
    auto_connect = True
    auto_reconnect = True
    nicknames = None
    ident = "dunamis"
    realname = "Dunamis IRC Bot"
    auth_user = ""
    auth_pass = ""
    auth_mech = 1  # SASL by default
    sasl_mech = 1  # PLAIN by default
    oper_auth = False
    oper_user = ""
    oper_pass = ""
    prefix = "!"

    try:
        opts, remaining = getopt(
            args,
            "a:p:s:",
            [
                "addresses=", "ports=", "ssl-ports=", "ssl=",
                "auto-connect=", "auto-reconnect=",
                "nick=", "ident=", "realname=",
                "auth-user=", "auth-pass=", "auth-mech=", "sasl-mech=",
                "oper", "oper-user=", "oper-pass=",
                "prefix="
            ]
        )

        for opt, arg in opts:
            if opt in ("-a", "--addresses"):
                addresses = [a.strip() for a in arg.split(',')]
            elif opt in ("-p", "--ports"):
                ports = [int(p.strip()) for p in arg.split(',')]
            elif opt == "--ssl-ports":
                ssl_ports = [int(p.strip()) for p in arg.split(',')]
            elif opt in ("-s", "--ssl"):
                enable_ssl = arg.lower() in ['true', 'yes', '1']
            elif opt == "--auto-connect":
                auto_connect = arg.lower() in ['true', 'yes', '1']
            elif opt == "--auto-reconnect":
                auto_reconnect = arg.lower() in ['true', 'yes', '1']
            elif opt == "--nick":
                nicknames = [n.strip() for n in arg.split(',')]
            elif opt == "--ident":
                ident = arg
            elif opt == "--realname":
                realname = arg
            elif opt == "--auth-user":
                auth_user = arg
            elif opt == "--auth-pass":
                auth_pass = arg
            elif opt == "--auth-mech":
                auth_mech = int(arg)
            elif opt == "--sasl-mech":
                sasl_mech = int(arg)
            elif opt == "--oper":
                oper_auth = True
            elif opt == "--oper-user":
                oper_user = arg
            elif opt == "--oper-pass":
                oper_pass = arg
            elif opt == "--prefix":
                prefix = arg

    except GetoptError as e:
        bot.send_message(target, f"Error: invalid option: {e}", nickname)
        return
    except ValueError as e:
        bot.send_message(target, f"Error: invalid value: {e}", nickname)
        return

    # Validate required fields
    if not addresses:
        bot.send_message(target, "Error: server address(es) required (-a ADDRESSES)", nickname)
        return

    # Set defaults
    if ports is None:
        ports = [6667]
    if ssl_ports is None:
        ssl_ports = [6697]
    if nicknames is None:
        nicknames = ["Dunamis", "Dunamis_", "Dunamis__"]

    # Add network to database
    try:
        network_id = bot.db.add_network(
            name=network_name,
            addresses=addresses,
            ports=ports,
            ssl_ports=ssl_ports,
            enable_ssl=enable_ssl,
            auto_connect=auto_connect,
            auto_reconnect=auto_reconnect,
            nicknames=nicknames,
            ident=ident,
            realname=realname,
            auth_mechanism=auth_mech,
            sasl_mechanism=sasl_mech,
            auth_username=auth_user,
            auth_password=auth_pass,
            oper_auth=oper_auth,
            oper_username=oper_user,
            oper_password=oper_pass,
            command_prefix=prefix
        )

        # Reload networks in network manager
        network_manager.load_networks()

        bot.send_message(
            target,
            f"Success: added network ID '{network_id}' to database. Use 'network connect {network_id}' to connect.",
            nickname
        )

    except Exception as e:
        bot.send_message(target, f"Error: failed to add network: {e}", nickname)


def handle_remove(bot, target: str, nickname: str, args: List[str]):
    network_manager = get_network_manager(bot)

    if not args:
        bot.send_message(target, "Usage: network remove <channel_id>", nickname)
        return

    try:
        network_id = int(args[0])
    except ValueError:
        bot.send_message(target, f"Error: invalid network ID: {args[0]}", nickname)
        return

    # Don't allow removing currently connected networks
    if network_id in network_manager.connectors:
        bot.send_message(
            target,
            f"Error: cannot remove connected network. Disconnect first with 'network disconnect {network_id}'",
            nickname
        )
        return

    # Remove from database
    try:
        network_name = network_manager.networks.get(network_id)
        if network_name:
            network_name = network_name.name
        else:
            network_name = str(network_id)

        if bot.db.remove_network(network_id):
            # Reload networks
            network_manager.load_networks()
            bot.send_message(
                target,
                f"Success: removed network ID '{network_id}' from database",
                nickname
            )
        else:
            bot.send_message(target, f"Error: network {network_id} not found", nickname)

    except Exception as e:
        bot.send_message(target, f"Error: failed to remove network: {e}", nickname)


def handle_modify(bot, target: str, nickname: str, args: List[str]):
    network_manager = get_network_manager(bot)

    if not args:
        bot.send_message(target, "Usage: network modify NETWORK_ID [OPTIONS]", nickname)
        return

    try:
        network_id = int(args[0])
    except ValueError:
        bot.send_message(target, f"Error: invalid network ID: {args[0]}", nickname)
        return

    remaining_args = args[1:]

    if not remaining_args:
        bot.send_message(target, "Error: no modifications specified", nickname)
        return

    # Parse modification options
    updates = {}

    try:
        opts, _ = getopt(
            remaining_args,
            "n:a:p:s:",
            [
                "name=", "addresses=", "ports=", "ssl-ports=", "ssl=",
                "auto-connect=", "auto-reconnect=",
                "nick=", "ident=", "realname=",
                "auth-user=", "auth-pass=", "auth-mech=", "sasl-mech=",
                "oper=", "oper-user=", "oper-pass=",
                "prefix="
            ]
        )

        for opt, arg in opts:
            if opt in ("-n", "--name"):
                updates['name'] = arg
            elif opt in ("-a", "--addresses"):
                updates['addresses'] = [a.strip() for a in arg.split(',')]
            elif opt in ("-p", "--ports"):
                updates['ports'] = [int(p.strip()) for p in arg.split(',')]
            elif opt == "--ssl-ports":
                updates['ssl_ports'] = [int(p.strip()) for p in arg.split(',')]
            elif opt in ("-s", "--ssl"):
                updates['enable_ssl'] = arg.lower() in ('true', 'yes', '1')
            elif opt == "--auto-connect":
                updates['auto_connect'] = arg.lower() in ('true', 'yes', '1')
            elif opt == "--auto-reconnect":
                updates['auto_reconnect'] = arg.lower() in ('true', 'yes', '1')
            elif opt == "--nick":
                updates['nicknames'] = [n.strip() for n in arg.split(',')]
            elif opt == "--ident":
                updates['ident'] = arg
            elif opt == "--realname":
                updates['realname'] = arg
            elif opt == "--auth-user":
                updates['auth_username'] = arg
            elif opt == "--auth-pass":
                updates['auth_password'] = arg
            elif opt == "--auth-mech":
                updates['auth_mechanism'] = int(arg)
            elif opt == "--sasl-mech":
                updates['sasl_mechanism'] = int(arg)
            elif opt == "--oper":
                updates['oper_auth'] = arg.lower() in ('true', 'yes', '1')
            elif opt == "--oper-user":
                updates['oper_username'] = arg
            elif opt == "--oper-pass":
                updates['oper_password'] = arg
            elif opt == "--prefix":
                updates['command_prefix'] = arg

    except GetoptError as e:
        bot.send_message(target, f"Error: invalid option: {e}", nickname)
        return
    except ValueError:
        bot.send_message(target, "Error: invalid value for numeric field", nickname)
        return

    # Warn if network is connected
    if network_id in network_manager.connectors:
        bot.send_message(
            target,
            f"Warning: network {network_id} is currently connected. Changes will take effect after reconnect.",
            nickname
        )

    # Update database
    try:
        if bot.db.update_network(network_id, updates):
            # Reload networks
            network_manager.load_networks()
            bot.send_message(
                target,
                f"Success: modified network: {network_id}",
                nickname
            )
        else:
            bot.send_message(target, f"Error: network not found: {network_id}", nickname)

    except Exception as e:
        bot.send_message(target, f"Error: failed to modify network: {e}", nickname)


__all__ = [
    'PLUGIN_INFO',
    'command_network',
]
