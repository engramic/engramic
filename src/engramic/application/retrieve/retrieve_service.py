# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import logging
from typing import TYPE_CHECKING

from engramic.application.retrieve.ask import Ask
from engramic.core import Prompt
from engramic.infrastructure.system.service import Service

if TYPE_CHECKING:
    from engramic.infrastructure.system.plugin_manager import PluginManager


class RetrieveService(Service):
    # ITERATIONS = 3

    def __init__(self, host) -> None:
        super().__init__(host)
        self.plugin_manager: PluginManager = host.plugin_manager

    def start(self) -> None:
        super().start()

        self.subscribe(Service.Topic.SUBMIT_PROMPT, self.on_submit_prompt)

    def on_submit_prompt(self, data):
        self.submit(Prompt(data))

    def submit(self, prompt: Prompt) -> None:
        retrieval = Ask(prompt, self.plugin_manager, super())
        retrieval.get_sources()

    def on_retrieve_complete(self, message):
        logging.info('message recieved. %s', message)  # just for testing
