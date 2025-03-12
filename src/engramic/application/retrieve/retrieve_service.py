# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from engramic.application.retrieve.ask import Ask
from engramic.core import Prompt
from engramic.infrastructure.system.plugin_manager import PluginManager
from engramic.infrastructure.system.service import Service


class RetrieveService(Service):
    # ITERATIONS = 3

    def __init__(self, plugin_manager: PluginManager) -> None:
        super().__init__()
        self.plugin_manager: PluginManager = plugin_manager

    def start(self, host) -> None:
        super().start(host)

    def submit(self, prompt: Prompt) -> None:
        retrieval = Ask(prompt, self.plugin_manager, super())
        retrieval.get_sources()
