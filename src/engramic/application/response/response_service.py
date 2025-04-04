# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import asyncio
import time
import uuid
from concurrent.futures import Future
from dataclasses import asdict
from enum import Enum
from typing import TYPE_CHECKING, Any

from engramic.application.response.prompt_main_prompt import PromptMainPrompt
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
        self.db_document_plugin = self.plugin_manager.get_plugin('db', 'document')
        self.engram_repository: EngramRepository = EngramRepository(self.db_document_plugin)
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

    def stop(self) -> None:
        self.run_task(self.web_socket_manager.shutdown())
        super().stop()

    def init_async(self) -> None:
        self.db_document_plugin['func'].connect(args=None)
        return super().init_async()

    def on_retrieve_complete(self, retrieve_result_in: dict[str, Any]) -> None:
        prompt_str = retrieve_result_in['prompt_str']
        prompt_analysis = PromptAnalysis(**retrieve_result_in['analysis'])
        retrieve_result = RetrieveResult(**retrieve_result_in['retrieve_response'])
        self.metrics_tracker.increment(ResponseMetric.RETRIEVES_RECIEVED)
        fetch_engrams_task = self.run_task(
            self.fetch_engrams(prompt_str=prompt_str, analysis=prompt_analysis, retrieve_result=retrieve_result)
        )
        fetch_engrams_task.add_done_callback(self.on_fetch_engrams_complete)

    """
    ### Fetch Engram

    Fetch engrams based on the IDs provided by the retrieve service.
    """

    async def fetch_engrams(
        self, prompt_str: str, analysis: PromptAnalysis, retrieve_result: RetrieveResult
    ) -> dict[str, Any]:
        engram_array: list[Engram] = await asyncio.to_thread(
            self.engram_repository.load_batch_retrieve_result, retrieve_result
        )

        # assembled main_prompt, render engrams.
        return {
            'prompt_str': prompt_str,
            'analysis': analysis,
            'retrieve_result': retrieve_result,
            'engram_array': engram_array,
        }

    def on_fetch_engrams_complete(self, fut: Future[Any]) -> None:
        exc = fut.exception()
        if exc is not None:
            raise exc
        result = fut.result()

        main_prompt_task = self.run_task(
            self.main_prompt(
                result['prompt_str'], result['analysis'], result['engram_array'], result['retrieve_result']
            )
        )
        main_prompt_task.add_done_callback(self.on_main_prompt_complete)

    """
    ### Main Prompt

    Combine the previous stages to generate the response.
    """

    async def main_prompt(
        self, prompt_str: str, analysis: PromptAnalysis, engram_array: list[Engram], retrieve_result: RetrieveResult
    ) -> Response:
        self.metrics_tracker.increment(ResponseMetric.ENGRAMS_FETCHED, len(engram_array))

        engram_dict_list = [asdict(engram) for engram in engram_array]

        # build main prompt here
        prompt = PromptMainPrompt(prompt_str=prompt_str, input_data={'engram_list': engram_dict_list})

        plugin = self.llm_main

        response = await asyncio.to_thread(
            plugin['func'].submit_streaming,
            prompt=prompt,
            websocket_manager=self.web_socket_manager,
            args=self.host.mock_update_args(plugin),
        )

        self.host.update_mock_data(self.llm_main, response)

        model = ''
        if plugin['args'].get('model'):
            model = plugin['args']['model']

        response_inst = Response(
            str(uuid.uuid4()), response[0]['llm_response'], retrieve_result, prompt.prompt_str, analysis, model
        )

        return response_inst

    def on_main_prompt_complete(self, fut: Future[Any]) -> None:
        result = fut.result()
        self.metrics_tracker.increment(ResponseMetric.MAIN_PROMPTS_RUN)
        self.send_message_async(Service.Topic.MAIN_PROMPT_COMPLETE, asdict(result))

    """
    ### Ack

    Acknowledge and return metrics
    """

    def on_acknowledge(self, message_in: str) -> None:
        del message_in

        metrics_packet: MetricPacket = self.metrics_tracker.get_and_reset_packet()

        self.send_message_async(
            Service.Topic.STATUS,
            {'id': self.id, 'name': self.__class__.__name__, 'timestamp': time.time(), 'metrics': metrics_packet},
        )
