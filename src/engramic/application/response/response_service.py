# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import time
import uuid
from dataclasses import asdict
from enum import Enum
from typing import TYPE_CHECKING, Any

from engramic.core import Engram, Prompt, PromptAnalysis
from engramic.core.host import Host
from engramic.core.metrics_tracker import MetricPacket, MetricsTracker
from engramic.core.response import Response
from engramic.core.retrieve_result import RetrieveResult
from engramic.infrastructure.repository.engram_repository import EngramRepository
from engramic.infrastructure.system.service import Service
from engramic.infrastructure.system.websocket_manager import WebsocketManager

if TYPE_CHECKING:
    from engramic.infrastructure.system.plugin_manager import PluginManager


class ResponseMetric(Enum):
    ENGRAMS_FETCHED = 'engrams_fetched'
    MAIN_PROMPTS_RUN = 'main_prompts_run'
    RETRIEVES_RECIEVED = 'retrieved_recieved'


class ResponseService(Service):
    def __init__(self, host: Host) -> None:
        super().__init__(host)
        self.plugin_manager: PluginManager = host.plugin_manager
        self.web_socket_manager: WebsocketManager = WebsocketManager(host)
        self.engram_repository: EngramRepository = EngramRepository(self.plugin_manager)
        self.llm_main = self.plugin_manager.get_plugin('llm', 'response_main')
        self.instructions: Prompt = Prompt('Placeholder for prompt engineering for main prompt.')
        self.metrics_tracker: MetricsTracker[ResponseMetric] = MetricsTracker[ResponseMetric]()
        ##
        # Many methods are not ready to be until their async component is running.
        # Do not call async context methods in the constructor.

    def start(self) -> None:
        self.subscribe(Service.Topic.ACKNOWLEDGE, self.on_acknowledge)
        self.subscribe(Service.Topic.RETRIEVE_COMPLETE, self.on_retrieve_complete)
        self.web_socket_manager.init_async()

    def on_retrieve_complete(self, retrieve_result_in: dict[str, Any]) -> None:
        prompt = Prompt(**retrieve_result_in['prompt'])
        prompt_analysis = PromptAnalysis(**retrieve_result_in['analysis'])
        retrieve_result = RetrieveResult(**retrieve_result_in['retrieve_response'])
        self.metrics_tracker.increment(ResponseMetric.RETRIEVES_RECIEVED)
        self.run_task(self.fetch_engrams(prompt=prompt, analysis=prompt_analysis, retrieve_result=retrieve_result))

    async def main_prompt(
        self, prompt: Prompt, analysis: PromptAnalysis, engram_array: list[Engram], retrieve_result: RetrieveResult
    ) -> None:
        self.metrics_tracker.increment(ResponseMetric.ENGRAMS_FETCHED, len(engram_array))

        # build main prompt here
        del engram_array

        mock_response = self.llm_main['func'].submit_streaming(
            prompt=self.instructions, args=self.llm_main['args'], websocket_manager=self.web_socket_manager
        )

        response = Response(str(uuid.uuid4()), mock_response[0], retrieve_result, prompt, analysis)

        self.metrics_tracker.increment(ResponseMetric.MAIN_PROMPTS_RUN)

        self.send_message_async(Service.Topic.MAIN_PROMPT_COMPLETE, asdict(response))

    async def fetch_engrams(self, prompt: Prompt, analysis: PromptAnalysis, retrieve_result: RetrieveResult) -> None:
        engram_array: list[Engram] = self.engram_repository.load_batch_retrieve_result(retrieve_result)
        # assembled main_prompt, render engrams.
        self.run_task(self.main_prompt(prompt, analysis, engram_array, retrieve_result))

    def on_acknowledge(self, message_in: str) -> None:
        del message_in

        metrics_packet: MetricPacket = self.metrics_tracker.get_and_reset_packet()

        self.send_message_async(
            Service.Topic.STATUS,
            {'id': self.id, 'name': self.__class__.__name__, 'timestamp': time.time(), 'metrics': metrics_packet},
        )
