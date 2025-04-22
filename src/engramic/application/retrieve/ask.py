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
    class Ask(Retrieval):
        """
        Ask is a specifc type of retrieval focused on traditional Q&A. It is a single instanc of an ask.

        This class handles the end-to-end workflow of transforming a raw prompt into
        contextual embeddings, querying the vector database, and returning retrieved engram ids.
        It also supports various conversation analysis and prompt index generation.

        Attributes:
            id (str): A unique identifier for this retrieval session.
            prompt (Prompt): The original prompt provided by the user.
            plugin_manager (PluginManager): Plugin manager used to access LLM, vector DB, and embedding components.
            metrics_tracker (MetricsTracker): Tracks operational metrics for observability.
            db_plugin (dict): Plugin used to interact with the document database.
            service (RetrieveService): Reference to the parent service coordinating this request.
            library (str | None): Optional name of the target library to search within.
            conversation_direction (dict[str, str]): Stores current user intent and working memory.
            prompt_analysis (PromptAnalysis | None): Stores structured analysis of the prompt after processing.

        Methods:
            get_sources():
                Initiates the async pipeline for directional memory retrieval.

            _fetch_history():
                Asynchronously retrieves prior user history from the document DB.

            _retrieve_gen_conversation_direction():
                Uses LLM plugin to extract user intent and conversational memory.

            _embed_gen_direction():
                Converts extracted intent into embeddings. General direction determines intent and manages short term memory.

            _vector_fetch_direction_meta():
                Queries the metadata collection in the vector DB using intent embeddings.

            _fetch_direction_meta():
                Loads Meta objects from the metadata store based on query results.

            _analyze_prompt():
                Uses LLM plugin to analyze the user prompt in the context of metadata.

            _generate_indices():
                Generates semantic indices from the prompt and metadata for retrieval.

            _generate_indicies_embeddings():
                Converts generated index phrases into embeddings.

            _query_index_db():
                Searches the main vector DB with embeddings to identify related engrams.

            on_fetch_history_complete(fut):
                Callback when prompt history fetch is complete; begins direction generation.

            on_direction_ret_complete(fut):
                Callback when conversation direction is generated; begins embedding.

            on_embed_direction_complete(fut):
                Callback when direction embedding is ready; begins vector DB search for metadata.

            on_vector_fetch_direction_meta_complete(fut):
                Callback when metadata vector search is complete; begins metadata fetch.

            on_fetch_direction_meta_complete(fut):
                Callback when metadata objects are fetched; begins analysis and index generation.

            on_analyze_complete(fut):
                Callback when prompt analysis and index generation are complete; begins embedding generation.

            on_indices_embeddings_generated(fut):
                Callback when index embeddings are ready; triggers main index DB query.

            on_query_index_db(fut):
                Final callback when engram retrieval is complete; assembles and emits the result.
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
        self.conversation_direction: dict[str, str]
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
        args['history'] = 10

        ret_val = await asyncio.to_thread(plugin['func'].fetch, table=DB.DBTables.HISTORY, ids=[], args=args)
        history_dict: list[dict[str, Any]] = ret_val[0]
        return history_dict

    def on_fetch_history_complete(self, fut: Future[Any]) -> None:
        response_array: list[dict[str, Any]] = fut.result()
        retrieve_gen_conversation_direction_step = self.service.run_task(
            self._retrieve_gen_conversation_direction(response_array)
        )
        retrieve_gen_conversation_direction_step.add_done_callback(self.on_direction_ret_complete)

    async def _retrieve_gen_conversation_direction(self, response_array: list[dict[str, Any]]) -> dict[str, str]:
        if __debug__:
            self.service.send_message_async(self.service.Topic.DEBUG_ASK_CREATED, {'ask_id': self.id})

        input_data = {'history_array': response_array}
        plugin = self.retrieve_gen_conversation_direction_plugin
        # add prompt engineering here and submit as the full prompt.
        prompt_gen = PromptGenConversation(prompt_str=self.prompt.prompt_str, input_data=input_data)

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
        )

        json_parsed: dict[str, str] = json.loads(ret[0]['llm_response'])

        self.conversation_direction = {}
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

        return json_parsed

    def on_direction_ret_complete(self, fut: Future[Any]) -> None:
        direction_ret = fut.result()

        logging.debug('current_user_intent: %s', direction_ret)
        intent_and_direction = direction_ret['current_user_intent']

        embed_step = self.service.run_task(self._embed_gen_direction(intent_and_direction))
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
        plugin['args'].update({'threshold': 0.6, 'n_results': 5})

        ret = await asyncio.to_thread(
            plugin['func'].query,
            collection_name='meta',
            embeddings=embedding,
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
        analyze_step = self.service.run_tasks([self._analyze_prompt(meta_list), self._generate_indices(meta_list)])
        analyze_step.add_done_callback(self.on_analyze_complete)

    """
    ### Prompt Analysis

    Analyzies the prompt and generates lookups that will aid in vector searching of related content
    """

    async def _analyze_prompt(self, meta_list: list[Meta]) -> dict[str, str]:
        plugin = self.prompt_analysis_plugin
        # add prompt engineering here and submit as the full prompt.
        prompt = PromptAnalyzePrompt(
            prompt_str=self.prompt.prompt_str,
            input_data={'meta_list': meta_list, 'working_memory': self.conversation_direction['working_memory']},
        )
        structured_response = {'response_length': str, 'user_prompt_type': str, 'thinking_steps': str}
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

        if __debug__:
            prompt_render = prompt.render_prompt()
            self.service.send_message_async(
                Service.Topic.DEBUG_ASK_INDICES,
                {'ask_id': self.id, 'prompt': prompt_render, 'indices': ret[0]['llm_response']},
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
        logging.debug('Query Result: %s', ret)

        if self.prompt_analysis is None:
            error = 'on_query_index_db failed: prompt_analysis is None and likely failed during an earlier process.'
            raise RuntimeError

        retrieve_result = RetrieveResult(
            self.id,
            engram_id_array=list(ret),
            conversation_direction=self.conversation_direction,
            analysis=asdict(self.prompt_analysis)['prompt_analysis'],
        )

        if self.prompt_analysis is None:
            error = 'Prompt analysis None in on_query_index_db'
            raise RuntimeError(error)

        retrieve_response = {
            'analysis': asdict(self.prompt_analysis),
            'prompt_str': self.prompt.prompt_str,
            'retrieve_response': asdict(retrieve_result),
        }

        if __debug__:
            self.service.host.update_mock_data_output(self.service, retrieve_response)

        self.service.send_message_async(Service.Topic.RETRIEVE_COMPLETE, retrieve_response)
