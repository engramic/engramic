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
from engramic.core.interface.db import DB
from engramic.core.retrieve_result import RetrieveResult
from engramic.infrastructure.system.plugin_manager import PluginManager  # noqa: TCH001
from engramic.infrastructure.system.service import Service

if TYPE_CHECKING:
    from concurrent.futures import Future

    from engramic.application.retrieve.retrieve_service import RetrieveService
    from engramic.core.metrics_tracker import MetricsTracker


class Ask(Retrieval):
    """
    Handles Q&A retrieval by transforming prompts into contextual embeddings and returning relevant engram IDs.

    This class implements the retrieval workflow from raw prompts to vector database queries,
    supporting conversation analysis and dynamic index generation.

    Attributes:
        id (str): Unique identifier for this retrieval session.
        prompt (Prompt): The original prompt provided by the user.
        service (RetrieveService): Parent service coordinating this request.
        metrics_tracker (MetricsTracker): Tracks operational metrics for observability.
        library (str | None): Optional target library to search within.
        widget_cmd (Any): Widget command from the prompt.
        conversation_direction (dict[str, Any]): Stores user intent and working memory.
        prompt_analysis (PromptAnalysis | None): Structured analysis of the prompt.
        new_conversation (bool): Flag indicating if this is a new conversation thread.
        type_filters (list[str]): Content type filters for vector database queries.

    Methods:
        get_sources() -> None:
            Initiates the async pipeline for directional memory retrieval.
        _fetch_history() -> list[dict[str, Any]]:
            Retrieves prior conversation history from the document database.
        on_fetch_history_complete(fut: Future[Any]) -> None:
            Processes history results and initiates conversation direction analysis.
        _retrieve_gen_conversation_direction(response_array: dict[str, Any]) -> None:
            Extracts user intent and conversational working memory using LLM analysis.
        on_direction_ret_complete(fut: Future[Any]) -> None:
            Processes conversation direction and initiates embedding generation.
        _embed_gen_direction() -> list[float]:
            Converts extracted user intent into vector embeddings.
        on_embed_direction_complete(fut: Future[Any]) -> None:
            Processes intent embeddings and initiates metadata retrieval.
        _vector_fetch_direction_meta(intent_embedding: list[float]) -> list[str]:
            Queries metadata collection using intent embeddings to find relevant context.
        on_vector_fetch_direction_meta_complete(fut: Future[Any]) -> None:
            Processes metadata IDs and loads full metadata objects.
        _fetch_direction_meta(meta_id: list[str]) -> list[Meta]:
            Loads Meta objects from metadata store for context enrichment.
        on_fetch_direction_meta_complete(fut: Future[Any]) -> None:
            Initiates parallel prompt analysis and index generation.
        _analyze_prompt() -> dict[str, Any]:
            Analyzes user prompt to determine response requirements and thinking steps.
        _generate_indices(meta_list: list[Meta]) -> dict[str, Any]:
            Generates semantic search indices based on prompt and metadata context.
        on_analyze_complete(fut: Future[Any]) -> None:
            Processes analysis results and initiates index embedding generation.
        _generate_indicies_embeddings(indices: list[str]) -> list[list[float]]:
            Converts generated index phrases into vector embeddings.
        on_indices_embeddings_generated(fut: Future[Any]) -> None:
            Processes index embeddings and initiates final vector database query.
        _query_index_db(embeddings: list[list[float]]) -> set[str]:
            Searches main vector database to identify related engram IDs.
        on_query_index_db(fut: Future[Any]) -> None:
            Finalizes retrieval results and sends completion message.
    """

    def __init__(
        self,
        ask_id: str,
        prompt: Prompt,
        plugin_manager: PluginManager,
        metrics_tracker: MetricsTracker[engramic.application.retrieve.retrieve_service.RetrieveMetric],
        db_plugin: dict[str, Any],
        service: RetrieveService,
        library: str | None = None,
    ) -> None:
        self.id = ask_id
        self.service = service
        self.metrics_tracker: MetricsTracker[engramic.application.retrieve.retrieve_service.RetrieveMetric] = (
            metrics_tracker
        )
        self.library = library
        self.prompt = prompt
        self.widget_cmd = None
        self.conversation_direction: dict[str, Any]
        self.prompt_analysis: PromptAnalysis | None = None
        self.retrieve_gen_conversation_direction_plugin = plugin_manager.get_plugin(
            'llm', 'retrieve_gen_conversation_direction'
        )
        self.prompt_analysis_plugin = plugin_manager.get_plugin('llm', 'retrieve_prompt_analysis')
        self.prompt_retrieve_indices_plugin = plugin_manager.get_plugin('llm', 'retrieve_gen_index')
        self.prompt_vector_db_plugin = plugin_manager.get_plugin('vector_db', 'db')
        self.prompt_db_document_plugin = db_plugin
        self.embeddings_gen_embed = plugin_manager.get_plugin('embedding', 'gen_embed')

    def get_sources(self) -> None:
        direction_step = self.service.run_task(self._fetch_history())
        direction_step.add_done_callback(self.on_fetch_history_complete)

    """
    ### CONVERSATION DIRECTION

    Fetches related domain knowledge based on the prompt intent.
    """

    async def _fetch_history(self) -> list[dict[str, Any]]:
        plugin = self.prompt_db_document_plugin
        args = plugin['args']
        args['history_limit'] = 1
        args['repo_ids_filters'] = self.prompt.repo_ids_filters
        args['conversation_id'] = self.prompt.conversation_id

        ret_val = await asyncio.to_thread(plugin['func'].fetch, table=DB.DBTables.HISTORY, ids=[], args=args)
        history_dict: list[dict[str, Any]] = ret_val[0]
        return history_dict

    def on_fetch_history_complete(self, fut: Future[Any]) -> None:
        response_array: dict[str, Any] = fut.result()

        if response_array['history']:
            self.new_conversation = (
                response_array['history'][0]['prompt']['conversation_id'] != self.prompt.conversation_id
            )
        else:
            self.new_conversation = True

        retrieve_gen_conversation_direction_step = self.service.run_task(
            self._retrieve_gen_conversation_direction(response_array)
        )
        retrieve_gen_conversation_direction_step.add_done_callback(self.on_direction_ret_complete)

    async def _retrieve_gen_conversation_direction(self, response_array: dict[str, Any]) -> None:
        if __debug__:
            self.service.send_message_async(self.service.Topic.DEBUG_ASK_CREATED, {'ask_id': self.id})

        input_data: dict[str, Any] = response_array

        plugin = self.retrieve_gen_conversation_direction_plugin

        if len(self.service.repo_folders.items()) > 0:
            input_data.update({'all_repos': self.service.repo_folders})
        else:
            input_data.update({'all_repos': None})

        self.conversation_direction = {}

        if self.prompt.widget_cmd:
            input_data.update({'current_engramic_widget': self.prompt.widget_cmd})

        # add prompt engineering here and submit as the full prompt.
        prompt_gen = PromptGenConversation(
            prompt_str=self.prompt.prompt_str, input_data=input_data, repo_ids_filters=self.prompt.repo_ids_filters
        )

        structured_schema = {
            'current_user_intent': str,
            'working_memory_step_1': str,
            'working_memory_step_2': str,
            'working_memory_step_3': str,
            'working_memory_step_4': str,
        }

        ret = await asyncio.to_thread(
            plugin['func'].submit,
            prompt=prompt_gen,
            structured_schema=structured_schema,
            args=self.service.host.mock_update_args(plugin),
            images=None,
        )

        json_parsed: dict[str, str] = json.loads(ret[0]['llm_response'])

        self.conversation_direction['current_user_intent'] = json_parsed['current_user_intent']
        self.conversation_direction['working_memory'] = json_parsed['working_memory_step_4']

        if __debug__:
            self.service.send_message_async(
                self.service.Topic.DEBUG_CONVERSATION_DIRECTION,
                {'ask_id': self.id, 'prompt': prompt_gen.render_prompt(), 'working_memory': ret[0]['llm_response']},
            )

        self.service.host.update_mock_data(plugin, ret)

        self.metrics_tracker.increment(
            engramic.application.retrieve.retrieve_service.RetrieveMetric.CONVERSATION_DIRECTION_CALCULATED
        )

    def on_direction_ret_complete(self, fut: Future[Any]) -> None:
        ret_val = fut.result()
        del ret_val

        embed_step = self.service.run_task(self._embed_gen_direction())
        embed_step.add_done_callback(self.on_embed_direction_complete)

    async def _embed_gen_direction(self) -> list[float]:
        plugin = self.embeddings_gen_embed

        ret = await asyncio.to_thread(
            plugin['func'].gen_embed,
            strings=[self.conversation_direction['current_user_intent']],
            args=self.service.host.mock_update_args(plugin),
        )

        self.service.host.update_mock_data(plugin, ret)

        float_array: list[float] = ret[0]['embeddings_list'][0]
        return float_array

    def on_embed_direction_complete(self, fut: Future[Any]) -> None:
        intent_embedding = fut.result()
        fetch_direction_step = self.service.run_task(self._vector_fetch_direction_meta(intent_embedding))
        fetch_direction_step.add_done_callback(self.on_vector_fetch_direction_meta_complete)

    async def _vector_fetch_direction_meta(self, intent_embedding: list[float]) -> list[str]:
        plugin = self.prompt_vector_db_plugin
        plugin['args'].update({'threshold': 0.6})  # meta needs a broader threshold.
        plugin['args'].update({'n_results': 2})  # num results per vector

        self.type_filters = ['native', 'episodic']

        if self.prompt.widget_cmd:
            self.type_filters.append('procedural')

        ret = await asyncio.to_thread(
            plugin['func'].query,
            collection_name='meta',
            embeddings=intent_embedding,
            repo_filters=self.prompt.repo_ids_filters,
            type_filters=self.type_filters,
            args=self.service.host.mock_update_args(plugin),
        )

        self.service.host.update_mock_data(plugin, ret)

        list_str: list[str] = ret[0]['query_set']
        # logging.warning(list_str)
        return list_str

    def on_vector_fetch_direction_meta_complete(self, fut: Future[Any]) -> None:
        meta_ids = fut.result()
        meta_fetch_step = self.service.run_task(self._fetch_direction_meta(meta_ids))
        meta_fetch_step.add_done_callback(self.on_fetch_direction_meta_complete)

    async def _fetch_direction_meta(self, meta_id: list[str]) -> list[Meta]:
        meta_list = self.service.meta_repository.load_batch(meta_id)

        if __debug__:
            dict_meta = [meta.summary_full.text if meta.summary_full is not None else '' for meta in meta_list]

            self.service.send_message_async(
                self.service.Topic.DEBUG_ASK_META, {'ask_id': self.id, 'ask_meta': dict_meta}
            )

        return meta_list

    def on_fetch_direction_meta_complete(self, fut: Future[Any]) -> None:
        meta_list = fut.result()
        analyze_step = self.service.run_tasks([self._analyze_prompt(), self._generate_indices(meta_list)])
        analyze_step.add_done_callback(self.on_analyze_complete)

    """
    ### Prompt Analysis

    Analyzies the prompt and generates lookups that will aid in vector searching of related content
    """

    async def _analyze_prompt(self) -> dict[str, Any]:
        plugin = self.prompt_analysis_plugin
        # add prompt engineering here and submit as the full prompt.
        prompt = PromptAnalyzePrompt(
            prompt_str=self.prompt.prompt_str,
            input_data={
                'working_memory': self.conversation_direction['working_memory'],
                'current_user_intent': self.conversation_direction['current_user_intent'],
            },
        )
        structured_response = {
            'response_length': str,
            'user_prompt_type': str,
            'thinking_steps': str,
            'remember_request': bool,
        }
        ret = await asyncio.to_thread(
            plugin['func'].submit,
            prompt=prompt,
            structured_schema=structured_response,
            args=self.service.host.mock_update_args(plugin),
            images=None,
        )

        self.service.host.update_mock_data(plugin, ret)

        self.metrics_tracker.increment(engramic.application.retrieve.retrieve_service.RetrieveMetric.PROMPTS_ANALYZED)

        if not isinstance(ret[0], dict):
            error = f'Expected dict[str, str], got {type(ret[0])}'
            raise TypeError(error)

        json_ret: dict[str, Any] = json.loads(ret[0]['llm_response'])
        return json_ret

    async def _generate_indices(self, meta_list: list[Meta]) -> dict[str, Any]:
        plugin = self.prompt_retrieve_indices_plugin
        # add prompt engineering here and submit as the full prompt.
        input_data: dict[str, Any] = {
            'meta_list': meta_list,
            'current_user_intent': self.conversation_direction['current_user_intent'],
        }

        if len(self.service.repo_folders.items()) > 0:
            input_data.update({'all_repos': self.service.repo_folders})
        else:
            input_data.update({'all_repos': None})

        prompt = PromptGenIndices(
            prompt_str=self.prompt.prompt_str, input_data=input_data, repo_ids_filters=self.prompt.repo_ids_filters
        )
        structured_output = {'indices': list[str]}
        ret = await asyncio.to_thread(
            plugin['func'].submit,
            prompt=prompt,
            structured_schema=structured_output,
            args=self.service.host.mock_update_args(plugin),
            images=None,
        )

        if __debug__:
            prompt_render = prompt.render_prompt()
            self.service.send_message_async(
                Service.Topic.DEBUG_ASK_INDICES,
                {'ask_id': self.id, 'prompt': prompt_render, 'indices': ret[0]['llm_response']},
            )

        self.service.host.update_mock_data(plugin, ret)
        response = ret[0]['llm_response']

        try:
            response_json = json.loads(response)
        except json.JSONDecodeError:
            logging.exception('Failed to parse JSON in _generate_indices: Response: %s', response)
            raise

        count = len(response_json['indices'])
        self.metrics_tracker.increment(
            engramic.application.retrieve.retrieve_service.RetrieveMetric.DYNAMIC_INDICES_GENERATED, count
        )

        if not isinstance(ret[0], dict):
            error = f'Expected dict[str, str], got {type(ret[0])}'
            raise TypeError(error)

        json_ret: dict[str, Any] = json.loads(ret[0]['llm_response'])
        return json_ret

    def on_analyze_complete(self, fut: Future[Any]) -> None:
        analysis = fut.result()  # This will raise an exception if the coroutine fails

        try:
            analysis_json = analysis['_analyze_prompt'][0]
            indices_json = analysis['_generate_indices'][0]
        except json.JSONDecodeError:
            logging.exception('Failed to parse JSON in on_analyze_complete')
            raise

        if self.prompt.widget_cmd:
            indices_json['indices'].append('widget ' + self.prompt.widget_cmd)

        self.prompt_analysis = PromptAnalysis(
            analysis_json,
            indices_json,
        )

        genrate_indices_future = self.service.run_task(
            self._generate_indicies_embeddings(self.prompt_analysis.indices['indices'])
        )
        genrate_indices_future.add_done_callback(self.on_indices_embeddings_generated)

    def on_indices_embeddings_generated(self, fut: Future[Any]) -> None:
        embeddings = fut.result()

        query_index_db_future = self.service.run_task(self._query_index_db(embeddings))
        query_index_db_future.add_done_callback(self.on_query_index_db)

    async def _generate_indicies_embeddings(self, indices: list[str]) -> list[list[float]]:
        plugin = self.embeddings_gen_embed

        if not indices:
            return []

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

        if not embeddings:
            return set()

        ids = set()

        ret = await asyncio.to_thread(
            plugin['func'].query,
            collection_name='main',
            embeddings=embeddings,
            repo_filters=self.prompt.repo_ids_filters,
            type_filters=self.type_filters,
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
        logging.debug('Query Result: %s', ret)

        if self.prompt_analysis is None:
            error = 'on_query_index_db failed: prompt_analysis is None and likely failed during an earlier process.'
            raise RuntimeError

        retrieve_result = RetrieveResult(
            self.id,
            self.prompt.prompt_id,
            engram_id_array=list(ret),
            conversation_direction=self.conversation_direction,
            analysis=asdict(self.prompt_analysis)['prompt_analysis'],
        )

        if self.prompt_analysis.prompt_analysis['remember_request']:
            self.prompt.training_mode = True

        if self.prompt_analysis is None:
            error = 'Prompt analysis None in on_query_index_db'
            raise RuntimeError(error)

        retrieve_response = {
            'analysis': asdict(self.prompt_analysis),
            'prompt': asdict(self.prompt),
            'retrieve_response': asdict(retrieve_result),
        }

        if __debug__:
            self.service.host.update_mock_data_output(self.service, retrieve_response)

        self.service.send_message_async(Service.Topic.RETRIEVE_COMPLETE, retrieve_response)
