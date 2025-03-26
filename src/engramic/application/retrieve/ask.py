# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from __future__ import annotations

import logging
from concurrent.futures import Future
from dataclasses import asdict
from typing import TYPE_CHECKING, Any

import engramic.application.retrieve.retrieve_service
from engramic.core import Prompt, PromptAnalysis, Retrieval
from engramic.core.retrieve_result import RetrieveResult
from engramic.infrastructure.system.plugin_manager import PluginManager  # noqa: TCH001
from engramic.infrastructure.system.service import Service

if TYPE_CHECKING:
    from engramic.core.metrics_tracker import MetricsTracker


class Ask(Retrieval):
    def __init__(
        self,
        prompt: Prompt,
        plugin_manager: PluginManager,
        metrics_tracker: MetricsTracker[engramic.application.retrieve.retrieve_service.RetrieveMetric],
        service: Service,
        library: str | None = None,
    ) -> None:
        self.service = service
        self.metrics_tracker: MetricsTracker[engramic.application.retrieve.retrieve_service.RetrieveMetric] = (
            metrics_tracker
        )
        self.library = library
        self.prompt = prompt
        self.prompt_analysis: PromptAnalysis | None = None
        self.retrieve_gen_conversation_direction_plugin = plugin_manager.get_plugin(
            'llm', 'retrieve_gen_conversation_direction'
        )
        self.prompt_analysis_plugin = plugin_manager.get_plugin('llm', 'retrieve_prompt_analysis')
        self.prompt_retrieve_indices_plugin = plugin_manager.get_plugin('llm', 'retrieve_gen_index')
        self.prompt_db_plugin = plugin_manager.get_plugin('vector_db', 'db')

    def get_sources(self) -> None:
        if (
            self.retrieve_gen_conversation_direction_plugin is None
            or self.prompt_analysis_plugin is None
            or self.prompt_retrieve_indices_plugin is None
            or self.prompt_db_plugin is None
        ):
            return None

        final_future: Future[list[str]] = Future()

        def on_direction_ret_complete(fut: Future[Any]) -> None:
            try:
                direction_ret = fut.result()

                direction = direction_ret['conversation_direction']

                logging.info(
                    'conversation direction: %s', direction
                )  # We will be using this later for anticipatory retrieval

                analyze_step = self.service.run_tasks([self._analyze_prompt(), self._generate_indices()])

                analyze_step.add_done_callback(on_analyze_complete)

            except Exception as e:
                logging.exception('Error in conversation direction generation')
                final_future.set_exception(e)

        def on_analyze_complete(fut: Future[Any]) -> None:
            try:
                analysis = fut.result()  # This will raise an exception if the coroutine fails

                self.prompt_analysis = PromptAnalysis(analysis['_analyze_prompt'], analysis['_generate_indices'])

                query_index_db_future = self.service.run_task(self._query_index_db())

                query_index_db_future.add_done_callback(on_query_index_db)

            except Exception as e:
                logging.exception('Error in analyzing prompt.')
                final_future.set_exception(e)

        def on_query_index_db(fut: Future[Any]) -> None:
            try:
                set_ret = fut.result()
                logging.info('Query Result: %s', set_ret)
                final_future.set_result(set_ret)
                result = final_future.result()
                retrieve_result = RetrieveResult(engram_id_array=list(result))

                if self.prompt_analysis is None:
                    error = 'Prompt analysis None in on_query_index_db'
                    raise RuntimeError(error)

                retrieve_response = {
                    'query': list(result),
                    'analysis': asdict(self.prompt_analysis),
                    'prompt': asdict(self.prompt),
                    'retrieve_response': asdict(retrieve_result),
                }
                self.service.send_message_async(Service.Topic.RETRIEVE_COMPLETE, retrieve_response)

            except Exception as e:
                logging.exception('Error in querying index DB.')
                final_future.set_exception(e)

        direction_step = self.service.run_task(self._retrieve_gen_conversation_direction())
        direction_step.add_done_callback(on_direction_ret_complete)

        return None

    async def _retrieve_gen_conversation_direction(self) -> dict[str, str]:
        plugin = self.retrieve_gen_conversation_direction_plugin
        # add prompt engineering here and submit as the full prompt.
        ret = plugin['func'].submit(prompt=self.prompt, args=plugin['args'])

        self.metrics_tracker.increment(
            engramic.application.retrieve.retrieve_service.RetrieveMetric.CONVERSATION_DIRECTION_CALCULATED
        )

        if not isinstance(ret[0], dict):
            error = f'Expected dict[str, str], got {type(ret[0])}'
            raise TypeError(error)

        return ret[0]

    async def _analyze_prompt(self) -> dict[str, str]:
        plugin = self.prompt_analysis_plugin
        # add prompt engineering here and submit as the full prompt.
        ret = plugin['func'].submit(prompt=self.prompt, args=plugin['args'])

        self.metrics_tracker.increment(engramic.application.retrieve.retrieve_service.RetrieveMetric.PROMPTS_ANALYZED)

        if not isinstance(ret[0], dict):
            error = f'Expected dict[str, str], got {type(ret[0])}'
            raise TypeError(error)

        return ret[0]

    async def _generate_indices(self) -> dict[str, str]:
        plugin = self.prompt_retrieve_indices_plugin
        # add prompt engineering here and submit as the full prompt.
        ret = plugin['func'].submit(prompt=self.prompt, args=plugin['args'])
        count = len(ret[0]['indices'])
        self.metrics_tracker.increment(
            engramic.application.retrieve.retrieve_service.RetrieveMetric.DYNAMIC_INDICES_GENERATED, count
        )

        if not isinstance(ret[0], dict):
            error = f'Expected dict[str, str], got {type(ret[0])}'
            raise TypeError(error)

        return ret[0]

    async def _query_index_db(self) -> set[str]:
        plugin = self.prompt_db_plugin
        # add prompt engineering here and submit as the full prompt.
        ret = plugin['func'].query(prompt=self.prompt, args=plugin['args'])
        num_queries = len(ret[0])
        self.metrics_tracker.increment(
            engramic.application.retrieve.retrieve_service.RetrieveMetric.VECTOR_DB_QUERIES, num_queries
        )

        if not isinstance(ret[0], set):
            error = f'Expected dict[str, str], got {type(ret[0])}'
            raise TypeError(error)

        return ret[0]
