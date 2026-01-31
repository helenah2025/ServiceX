"""
Test Plugin for Dunamis
Provides entertainment and novelty commands for IRC bot

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

PLUGIN_INFO = {
    "name": "Test",
    "author": "Helenah, Helena Bolan",
    "version": "1.0",
    "description": "Test Plugin for Dunamis"
}

def value_test(bot) -> str:
    return "test"

def command_test(bot, target: str, nickname: str, args: List[str]):
    message = "test"
    bot.send_message(target, message, nickname)
    print(dir(bot))
