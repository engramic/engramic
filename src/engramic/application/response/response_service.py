# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import uuid
from dataclasses import asdict
from typing import TYPE_CHECKING

from engramic.core import Engram, Prompt
from engramic.core.response import Response
from engramic.infrastructure.repository.engram_repository import EngramRepository
from engramic.infrastructure.system.service import Service
from engramic.infrastructure.system.websocket_manager import WebsocketManager

if TYPE_CHECKING:
    from engramic.infrastructure.system.plugin_manager import PluginManager


class ResponseService(Service):
    def __init__(self, host) -> None:
        super().__init__(host)
        self.plugin_manager: PluginManager = host.plugin_manager
        self.web_socket_manager: WebsocketManager = WebsocketManager(host)
        self.engram_repository: EngramRepository = EngramRepository(self.plugin_manager)
        self.llm_main = self.plugin_manager.get_plugin('llm', 'response_main')
        self.prompt = Prompt('Placeholder for prompt engineering for main prompt.')
        ##
        # Many methods are not ready to be until their async component is running.
        # Do not call async context methods in the constructor.

    def start(self):
        self.subscribe(Service.Topic.RETRIEVE_COMPLETE, self.on_retrieve_complete)
        self.web_socket_manager.init_async()

    def on_retrieve_complete(self, engram_ids: list[uuid.UUID]):
        self.run_task(self.fetch_engrams(engram_ids=engram_ids))

    async def submit_llm(self, engram_array):
        mock_response = self.llm_main['func'].submit_streaming(
            prompt=self.prompt, args=self.llm_main['args'], websocket_manager=self.web_socket_manager
        )
        response = Response(mock_response[0], engram_array)
        self.send_message_async(Service.Topic.MAIN_PROMPT_COMPLETE, asdict(response))

    async def fetch_engrams(self, engram_ids: list[uuid.UUID]):
        engram_array: list[Engram] = self.engram_repository.load_batch(engram_ids)
        del engram_array  # to be replaced.
        # assembled main_prompt, render engrams.
        self.run_task(self.submit_llm(engram_ids))
