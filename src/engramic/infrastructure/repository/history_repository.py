# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from dataclasses import asdict

from engramic.core.response import Response
from engramic.infrastructure.system.plugin_manager import PluginManager


class HistoryRepository:
    def __init__(self, plugin_manager: PluginManager) -> None:
        self.db_plugin = plugin_manager.get_plugin('db', 'document')
        self.is_connected = self.db_plugin['func'].connect()

    def save_history(self, response: Response) -> None:
        self.db_plugin['func'].execute_data(query='save_history', data=asdict(response))
