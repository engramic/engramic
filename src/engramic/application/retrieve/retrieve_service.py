# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import logging

from engramic.application.retrieve.ask import Ask
from engramic.core import Prompt
from engramic.infrastructure.system.plugin_manager import PluginManager
from engramic.infrastructure.system.service import Service


class RetrieveService(Service):
    # ITERATIONS = 3

    def __init__(self, plugin_manager: PluginManager, host) -> None:
        super().__init__(host)
        self.plugin_manager: PluginManager = plugin_manager

    def start(self) -> None:
        super().start()
        # self.subscribe(Service.Topic.RETRIEVE_COMPLETE, self.on_retrieve_complete)  # just for testing

    def submit(self, prompt: Prompt) -> None:
        retrieval = Ask(prompt, self.plugin_manager, super())
        retrieval.get_sources()

    def on_retrieve_complete(self, message):
        logging.info('message recieved. %s', message)  # just for testing
