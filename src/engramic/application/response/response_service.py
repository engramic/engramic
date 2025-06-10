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
from engramic.core import Engram, PromptAnalysis
from engramic.core.host import Host
from engramic.core.interface.db import DB
from engramic.core.metrics_tracker import MetricPacket, MetricsTracker
from engramic.core.prompt import Prompt
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
    """
    Orchestrates AI response generation by integrating retrieval results, historical context, and prompt engineering.

    Coordinates plugin-managed large language models (LLMs), websockets for streaming responses,
    and tracks metrics throughout the response generation pipeline.

    Attributes:
        plugin_manager (PluginManager): Provides access to LLM and DB plugins.
        web_socket_manager (WebsocketManager): Manages live streaming over websocket.
        db_document_plugin (dict): Document store plugin interface.
        engram_repository (EngramRepository): Access point for loading engrams.
        llm_main (dict): Plugin for executing the main LLM-based response generation.
        metrics_tracker (MetricsTracker): Tracks internal response metrics.

    Methods:
        start() -> None:
            Subscribes to service topics and initializes websocket manager.
        stop() -> None:
            Shuts down the websocket manager and stops the service.
        init_async() -> None:
            Initializes the DB plugin connection asynchronously.
        on_retrieve_complete(retrieve_result_in: dict[str, Any]) -> None:
            Processes retrieval results and initiates engram and history fetch.
        _fetch_history(prompt: Prompt) -> dict[str, Any]:
            Asynchronously fetches historical conversation context.
        _fetch_retrieval(prompt: Prompt, source_id: str, analysis: PromptAnalysis, retrieve_result: RetrieveResult) -> dict[str, Any]:
            Loads engrams using retrieve result.
        on_fetch_data_complete(fut: Future[Any]) -> None:
            Launches main prompt generation after history and engrams are loaded.
        main_prompt(prompt_in: Prompt, source_id: str, analysis: PromptAnalysis, engram_array: list[Engram], retrieve_result: RetrieveResult, history_array: dict[str, Any]) -> Response:
            Constructs and submits the main prompt to the LLM plugin.
        on_main_prompt_complete(fut: Future[Any]) -> None:
            Sends generated response and updates metrics.
        on_acknowledge(message_in: str) -> None:
            Sends current metrics snapshot to monitoring topics.
    """

    def __init__(self, host: Host) -> None:
        super().__init__(host)
        self.plugin_manager: PluginManager = host.plugin_manager
        self.web_socket_manager: WebsocketManager = WebsocketManager(host)
        self.db_document_plugin = self.plugin_manager.get_plugin('db', 'document')
        self.engram_repository: EngramRepository = EngramRepository(self.db_document_plugin)
        self.llm_main = self.plugin_manager.get_plugin('llm', 'response_main')
        self.metrics_tracker: MetricsTracker[ResponseMetric] = MetricsTracker[ResponseMetric]()
        ##
        # Many methods are not ready to be until their async component is running.
        # Do not call async context methods in the constructor.

    def start(self) -> None:
        self.subscribe(Service.Topic.ACKNOWLEDGE, self.on_acknowledge)
        self.subscribe(Service.Topic.RETRIEVE_COMPLETE, self.on_retrieve_complete)
        self.web_socket_manager.init_async()
        super().start()

    async def stop(self) -> None:
        await self.web_socket_manager.shutdown()

    def init_async(self) -> None:
        self.db_document_plugin['func'].connect(args=None)
        return super().init_async()

    def on_retrieve_complete(self, retrieve_result_in: dict[str, Any]) -> None:
        if __debug__:
            self.host.update_mock_data_input(self, retrieve_result_in)

        prompt = Prompt(**retrieve_result_in['prompt'])
        prompt_analysis = PromptAnalysis(**retrieve_result_in['analysis'])
        retrieve_result = RetrieveResult(**retrieve_result_in['retrieve_response'])
        source_id = retrieve_result.source_id
        self.metrics_tracker.increment(ResponseMetric.RETRIEVES_RECIEVED)
        fetch_engrams_task = self.run_tasks([
            self._fetch_retrieval(
                prompt=prompt, source_id=source_id, analysis=prompt_analysis, retrieve_result=retrieve_result
            ),
            self._fetch_history(prompt),
        ])
        fetch_engrams_task.add_done_callback(self.on_fetch_data_complete)

    """
    ### Fetch History & Engram

    Fetch engrams based on the IDs provided by the retrieve service.
    """

    async def _fetch_history(self, prompt: Prompt) -> dict[str, Any]:
        plugin = self.db_document_plugin
        args = plugin['args']
        args['history'] = 1
        args['repo_ids_filters'] = prompt.repo_ids_filters

        ret_val = await asyncio.to_thread(plugin['func'].fetch, table=DB.DBTables.HISTORY, ids=[], args=args)
        history: dict[str, Any] = ret_val[0]
        return history

    async def _fetch_retrieval(
        self, prompt: Prompt, source_id: str, analysis: PromptAnalysis, retrieve_result: RetrieveResult
    ) -> dict[str, Any]:
        engram_array: list[Engram] = await asyncio.to_thread(
            self.engram_repository.load_batch_retrieve_result, retrieve_result
        )

        # assembled main_prompt, render engrams.
        return {
            'prompt': prompt,
            'source_id': source_id,
            'analysis': analysis,
            'retrieve_result': retrieve_result,
            'engram_array': engram_array,
        }

    def on_fetch_data_complete(self, fut: Future[Any]) -> None:
        exc = fut.exception()
        if exc is not None:
            raise exc
        result = fut.result()
        retrieval = result['_fetch_retrieval'][0]
        history = result['_fetch_history'][0]

        main_prompt_task = self.run_task(
            self.main_prompt(
                retrieval['prompt'],
                retrieval['source_id'],
                retrieval['analysis'],
                retrieval['engram_array'],
                retrieval['retrieve_result'],
                history,
            )
        )
        main_prompt_task.add_done_callback(self.on_main_prompt_complete)

    """
    ### Main Prompt

    Combine the previous stages to generate the response.
    """

    async def main_prompt(
        self,
        prompt_in: Prompt,
        source_id: str,
        analysis: PromptAnalysis,
        engram_array: list[Engram],
        retrieve_result: RetrieveResult,
        history_array: dict[str, Any],
    ) -> Response:
        self.metrics_tracker.increment(ResponseMetric.ENGRAMS_FETCHED, len(engram_array))

        engram_dict_list = [asdict(engram) for engram in engram_array]

        # build main prompt here
        prompt = PromptMainPrompt(
            prompt_str=prompt_in.prompt_str,
            is_lesson=prompt_in.is_lesson,
            training_mode=prompt_in.training_mode,
            repo_ids_filters=prompt_in.repo_ids_filters,
            input_data={
                'engram_list': engram_dict_list,
                'history': history_array['history'],
                'working_memory': retrieve_result.conversation_direction,
                'analysis': retrieve_result.analysis,
            },
        )

        plugin = self.llm_main
        args = self.host.mock_update_args(plugin)

        if prompt_in.is_lesson:
            response = await asyncio.to_thread(
                plugin['func'].submit, prompt=prompt, args=args, images=None, structured_schema=None
            )
        else:
            response = await asyncio.to_thread(
                plugin['func'].submit_streaming,
                prompt=prompt,
                websocket_manager=self.web_socket_manager,
                args=args,
            )

        if __debug__:
            main_prompt = prompt.render_prompt()
            self.send_message_async(
                Service.Topic.DEBUG_MAIN_PROMPT_INPUT, {'main_prompt': main_prompt, 'ask_id': retrieve_result.ask_id}
            )

        self.host.update_mock_data(self.llm_main, response)

        model = ''
        if plugin['args'].get('model'):
            model = plugin['args']['model']

        response = response[0]['llm_response'].replace('$', 'USD ').replace('<context>', '').replace('</context>', '')

        response_inst = Response(str(uuid.uuid4()), source_id, response, retrieve_result, prompt_in, analysis, model)

        return response_inst

    def on_main_prompt_complete(self, fut: Future[Any]) -> None:
        result = fut.result()
        self.metrics_tracker.increment(ResponseMetric.MAIN_PROMPTS_RUN)

        self.send_message_async(Service.Topic.MAIN_PROMPT_COMPLETE, asdict(result))

        if __debug__:
            self.host.update_mock_data_output(self, asdict(result))

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
