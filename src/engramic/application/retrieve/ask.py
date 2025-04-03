# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import asdict
from typing import TYPE_CHECKING, Any

import engramic.application.retrieve.retrieve_service
from engramic.application.retrieve.prompt_analyze_prompt import PromptAnalyzePrompt
from engramic.application.retrieve.prompt_gen_conversation import PromptGenConversation
from engramic.application.retrieve.prompt_gen_indices import PromptGenIndices
from engramic.core import Meta, Prompt, PromptAnalysis, Retrieval
from engramic.core.retrieve_result import RetrieveResult
from engramic.infrastructure.system.plugin_manager import PluginManager  # noqa: TCH001
from engramic.infrastructure.system.service import Service

if TYPE_CHECKING:
    from concurrent.futures import Future

    from engramic.application.retrieve.retrieve_service import RetrieveService
    from engramic.core.metrics_tracker import MetricsTracker


class Ask(Retrieval):
    def __init__(
        self,
        prompt: Prompt,
        plugin_manager: PluginManager,
        metrics_tracker: MetricsTracker[engramic.application.retrieve.retrieve_service.RetrieveMetric],
        service: RetrieveService,
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
        self.prompt_vector_db_plugin = plugin_manager.get_plugin('vector_db', 'db')
        self.embeddings_gen_embed = plugin_manager.get_plugin('embedding', 'gen_embed')

    def get_sources(self) -> None:
        direction_step = self.service.run_task(self._retrieve_gen_conversation_direction())
        direction_step.add_done_callback(self.on_direction_ret_complete)

    """
    ### CONVERSATION DIRECTION

    Fetches related domain knowledge based on the prompt intent.
    """

    async def _retrieve_gen_conversation_direction(self) -> dict[str, str]:
        plugin = self.retrieve_gen_conversation_direction_plugin
        # add prompt engineering here and submit as the full prompt.
        prompt_gen = PromptGenConversation(prompt_str=self.prompt.prompt_str)

        structured_schema = {'user_intent': str, 'perform_research': bool}

        ret = await asyncio.to_thread(
            plugin['func'].submit,
            prompt=prompt_gen,
            structured_schema=structured_schema,
            args=self.service.host.mock_update_args(plugin),
        )

        self.service.host.update_mock_data(plugin, ret)

        json_parsed: dict[str, str] = json.loads(ret[0]['llm_response'])
        self.metrics_tracker.increment(
            engramic.application.retrieve.retrieve_service.RetrieveMetric.CONVERSATION_DIRECTION_CALCULATED
        )

        return json_parsed

    def on_direction_ret_complete(self, fut: Future[Any]) -> None:
        direction_ret = fut.result()

        logging.info('user_intent: %s', direction_ret)  # We will be using this later for anticipatory retrieval

        embed_step = self.service.run_task(self._embed_gen_direction(direction_ret['user_intent']))
        embed_step.add_done_callback(self.on_embed_direction_complete)

    async def _embed_gen_direction(self, main_prompt: str) -> list[float]:
        plugin = self.embeddings_gen_embed
        ret = await asyncio.to_thread(
            plugin['func'].gen_embed, strings=[main_prompt], args=self.service.host.mock_update_args(plugin)
        )

        self.service.host.update_mock_data(plugin, ret)

        float_array: list[float] = ret[0]['embeddings_list'][0]
        return float_array

    def on_embed_direction_complete(self, fut: Future[Any]) -> None:
        embedding = fut.result()
        fetch_direction_step = self.service.run_task(self._vector_fetch_direction_meta(embedding))
        fetch_direction_step.add_done_callback(self.on_vector_fetch_direction_meta_complete)

    async def _vector_fetch_direction_meta(self, embedding: list[float]) -> list[str]:
        plugin = self.prompt_vector_db_plugin
        plugin['args'].update({'threshold': 1, 'n_results': 10})

        ret = await asyncio.to_thread(
            plugin['func'].query,
            collection_name='meta',
            embeddings=embedding,
            args=self.service.host.mock_update_args(plugin),
        )

        self.service.host.update_mock_data(plugin, ret)

        list_str: list[str] = ret[0]['query_set']
        return list_str

    def on_vector_fetch_direction_meta_complete(self, fut: Future[Any]) -> None:
        meta_ids = fut.result()
        meta_fetch_step = self.service.run_task(self._fetch_direction_meta(meta_ids))
        meta_fetch_step.add_done_callback(self.on_fetch_direction_meta_complete)

    async def _fetch_direction_meta(self, meta_id: list[str]) -> list[Meta]:
        meta_list = self.service.meta_repository.load_batch(meta_id)
        return meta_list

    def on_fetch_direction_meta_complete(self, fut: Future[Any]) -> None:
        meta_list = fut.result()
        analyze_step = self.service.run_tasks([self._analyze_prompt(meta_list), self._generate_indices(meta_list)])
        analyze_step.add_done_callback(self.on_analyze_complete)

    """
    ### Prompt Analysis

    Analyzies the prompt and generates lookups that will aid in vector searching of related content
    """

    async def _analyze_prompt(self, meta_list: list[Meta]) -> dict[str, str]:
        plugin = self.prompt_analysis_plugin
        # add prompt engineering here and submit as the full prompt.
        prompt = PromptAnalyzePrompt(prompt_str=self.prompt.prompt_str, input_data={'meta_list': meta_list})
        structured_response = {'response_length': str}
        ret = await asyncio.to_thread(
            plugin['func'].submit,
            prompt=prompt,
            structured_schema=structured_response,
            args=self.service.host.mock_update_args(plugin),
        )

        self.service.host.update_mock_data(plugin, ret)

        self.metrics_tracker.increment(engramic.application.retrieve.retrieve_service.RetrieveMetric.PROMPTS_ANALYZED)

        if not isinstance(ret[0], dict):
            error = f'Expected dict[str, str], got {type(ret[0])}'
            raise TypeError(error)

        return ret[0]

    def on_analyze_complete(self, fut: Future[Any]) -> None:
        analysis = fut.result()  # This will raise an exception if the coroutine fails

        self.prompt_analysis = PromptAnalysis(
            json.loads(analysis['_analyze_prompt'][0]['llm_response']),
            json.loads(analysis['_generate_indices'][0]['llm_response']),
        )

        genrate_indices_future = self.service.run_task(
            self._generate_indicies_embeddings(self.prompt_analysis.indices['indices'])
        )
        genrate_indices_future.add_done_callback(self.on_indices_embeddings_generated)

    async def _generate_indices(self, meta_list: list[Meta]) -> dict[str, str]:
        plugin = self.prompt_retrieve_indices_plugin
        # add prompt engineering here and submit as the full prompt.
        prompt = PromptGenIndices(prompt_str=self.prompt.prompt_str, input_data={'meta_list': meta_list})
        structured_output = {'indices': list[str]}
        ret = await asyncio.to_thread(
            plugin['func'].submit,
            prompt=prompt,
            structured_schema=structured_output,
            args=self.service.host.mock_update_args(plugin),
        )

        self.service.host.update_mock_data(plugin, ret)
        response = ret[0]['llm_response']
        response_json = json.loads(response)
        count = len(response_json['indices'])
        self.metrics_tracker.increment(
            engramic.application.retrieve.retrieve_service.RetrieveMetric.DYNAMIC_INDICES_GENERATED, count
        )

        if not isinstance(ret[0], dict):
            error = f'Expected dict[str, str], got {type(ret[0])}'
            raise TypeError(error)

        return ret[0]

    def on_indices_embeddings_generated(self, fut: Future[Any]) -> None:
        embeddings = fut.result()

        query_index_db_future = self.service.run_task(self._query_index_db(embeddings))
        query_index_db_future.add_done_callback(self.on_query_index_db)

    async def _generate_indicies_embeddings(self, indices: list[str]) -> list[list[float]]:
        plugin = self.embeddings_gen_embed

        ret = await asyncio.to_thread(
            plugin['func'].gen_embed, strings=indices, args=self.service.host.mock_update_args(plugin)
        )

        self.service.host.update_mock_data(plugin, ret)
        embeddings_list: list[list[float]] = ret[0]['embeddings_list']
        return embeddings_list

    """
    ### Fetch Engram IDs

    Use the indices to fetch related Engram IDs
    """

    async def _query_index_db(self, embeddings: list[list[float]]) -> set[str]:
        plugin = self.prompt_vector_db_plugin

        ids = set()

        ret = await asyncio.to_thread(
            plugin['func'].query,
            collection_name='main',
            embeddings=embeddings,
            args=self.service.host.mock_update_args(plugin),
        )

        self.service.host.update_mock_data(plugin, ret)
        ids.update(ret[0]['query_set'])

        num_queries = len(ids)
        self.metrics_tracker.increment(
            engramic.application.retrieve.retrieve_service.RetrieveMetric.VECTOR_DB_QUERIES, num_queries
        )

        return ids

    def on_query_index_db(self, fut: Future[Any]) -> None:
        ret = fut.result()
        logging.info('Query Result: %s', ret)

        retrieve_result = RetrieveResult(engram_id_array=list(ret))

        if self.prompt_analysis is None:
            error = 'Prompt analysis None in on_query_index_db'
            raise RuntimeError(error)

        retrieve_response = {
            'analysis': asdict(self.prompt_analysis),
            'prompt_str': self.prompt.prompt_str,
            'retrieve_response': asdict(retrieve_result),
        }

        self.service.send_message_async(Service.Topic.RETRIEVE_COMPLETE, retrieve_response)
