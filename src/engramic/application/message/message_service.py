# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from engramic.infrastructure.system.base_message_service import BaseMessageService
from engramic.infrastructure.system.plugin_manager import PluginManager


class MessageService(BaseMessageService):
    # ITERATIONS = 3

    def __init__(self, plugin_manager: PluginManager) -> None:
        super().__init__()
        self.plugin_manager: PluginManager = plugin_manager

    def start(self, host) -> None:
        super().start(host)
