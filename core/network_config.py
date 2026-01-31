"""
Dunamis IRC Bot - Network Configuration

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

from __future__ import annotations
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class NetworkConfig:
    id: int
    name: str
    addresses: List[str]
    ports: List[int]
    ssl_ports: List[int]
    enable_ssl: bool
    auto_connect: bool
    auto_reconnect: bool
    nicknames: List[str]
    ident: str
    realname: str
    auth_mechanism: int  # 0=None, 1=SASL, 2=NickServ, 3=Custom
    sasl_mechanism: int  # 0=None, 1=PLAIN, 2=EXTERNAL
    auth_username: str
    auth_password: str
    oper_auth: bool
    oper_username: str
    oper_password: str
    command_prefix: str
    rpl_welcome: Optional[str] = None
    rpl_yourhost: Optional[str] = None
    rpl_created: Optional[str] = None
    rpl_myinfo: Optional[str] = None
    rpl_isupport: Optional[str] = None
    rpl_visiblehost: Optional[str] = None

    @property
    def primary_nickname(self) -> str:
        return self.nicknames[0] if self.nicknames else "Dunamis"

    @property
    def primary_address(self) -> str:
        return self.addresses[0] if self.addresses else "localhost"

    @property
    def primary_port(self) -> int:
        ports = self.ssl_ports if self.enable_ssl else self.ports
        return ports[0] if ports else 6667

    def get_next_address(self, current: str) -> Optional[str]:
        if not self.addresses:
            return self.primary_address
        try:
            idx = self.addresses.index(current)
            return self.addresses[(idx + 1) % len(self.addresses)]
        except (ValueError, IndexError):
            return self.primary_address

    def get_next_port(self, current: int) -> Optional[int]:
        port_list = self.ssl_ports if self.enable_ssl else self.ports
        if not port_list:
            return self.primary_port
        try:
            idx = port_list.index(current)
            return port_list[(idx + 1) % len(port_list)]
        except (ValueError, IndexError):
            return self.primary_port

    def get_next_nickname(self, current: str) -> Optional[str]:
        if not self.nicknames:
            return self.primary_nickname
        try:
            idx = self.nicknames.index(current)
            return self.nicknames[(idx + 1) % len(self.nicknames)]
        except (ValueError, IndexError):
            return self.primary_nickname
