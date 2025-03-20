# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import uuid
from dataclasses import asdict
from typing import TYPE_CHECKING, Any

from engramic.core import Engram, Prompt, PromptAnalysis
from engramic.core.response import Response
from engramic.core.retrieve_result import RetrieveResult
from engramic.infrastructure.repository.engram_repository import EngramRepository
from engramic.infrastructure.system.host import Host
from engramic.infrastructure.system.service import Service
from engramic.infrastructure.system.websocket_manager import WebsocketManager

if TYPE_CHECKING:
    from engramic.infrastructure.system.plugin_manager import PluginManager


class ResponseService(Service):
    def __init__(self, host: Host) -> None:
        super().__init__(host)
        self.plugin_manager: PluginManager = host.plugin_manager
        self.web_socket_manager: WebsocketManager = WebsocketManager(host)
        self.engram_repository: EngramRepository = EngramRepository(self.plugin_manager)
        self.llm_main = self.plugin_manager.get_plugin('llm', 'response_main')
        self.instructions: Prompt = Prompt('Placeholder for prompt engineering for main prompt.')
        ##
        # Many methods are not ready to be until their async component is running.
        # Do not call async context methods in the constructor.

    def start(self) -> None:
        self.subscribe(Service.Topic.RETRIEVE_COMPLETE, self.on_retrieve_complete)
        self.web_socket_manager.init_async()

    def on_retrieve_complete(self, retrieve_result_in: dict[str, Any]) -> None:
        prompt = Prompt(**retrieve_result_in['prompt'])
        prompt_analysis = PromptAnalysis(**retrieve_result_in['analysis'])
        retrieve_result = RetrieveResult(**retrieve_result_in['retrieve_response'])
        self.run_task(self.fetch_engrams(prompt=prompt, analysis=prompt_analysis, retrieve_result=retrieve_result))

    async def main_prompt(
        self, prompt: Prompt, analysis: PromptAnalysis, engram_array: list[Engram], retrieve_result: RetrieveResult
    ) -> None:
        # build main prompt here
        del engram_array

        mock_response = self.llm_main['func'].submit_streaming(
            prompt=self.instructions, args=self.llm_main['args'], websocket_manager=self.web_socket_manager
        )

        response = Response(str(uuid.uuid4()), mock_response[0], retrieve_result, prompt, analysis)

        self.send_message_async(Service.Topic.MAIN_PROMPT_COMPLETE, asdict(response))

    async def fetch_engrams(self, prompt: Prompt, analysis: PromptAnalysis, retrieve_result: RetrieveResult) -> None:
        engram_array: list[Engram] = self.engram_repository.load_batch_retrieve_result(retrieve_result)
        # assembled main_prompt, render engrams.
        self.run_task(self.main_prompt(prompt, analysis, engram_array, retrieve_result))
