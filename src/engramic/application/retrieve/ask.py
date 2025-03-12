# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import logging
from concurrent.futures import Future

from engramic.core import Library, Prompt, Retrieval
from engramic.infrastructure.system.plugin_manager import PluginManager
from engramic.infrastructure.system.service import Service


class Ask(Retrieval):
    def __init__(
        self,
        prompt: Prompt,
        plugin_manager: PluginManager,
        service: Service,
        library: Library = None,
    ) -> None:
        self.service = service
        self.library = library
        self.prompt = prompt
        self.retrieve_gen_conversation_direction_plugin = plugin_manager.get_plugin(
            'llm', 'retrieve_gen_conversation_direction'
        )
        self.prompt_analysis_plugin = plugin_manager.get_plugin('llm', 'retrieve_prompt_analysis')
        self.prompt_retrieve_indicies_plugin = plugin_manager.get_plugin('llm', 'retrieve_gen_index')
        self.prompt_query_index_db_plugin = plugin_manager.get_plugin('vector_db', 'query')

    def get_sources(self) -> None:
        if (
            self.retrieve_gen_conversation_direction_plugin is None
            or self.prompt_analysis_plugin is None
            or self.prompt_retrieve_indicies_plugin is None
            or self.prompt_query_index_db_plugin is None
        ):
            return None

        direction_step = self.service.submit_async_tasks(self._retrieve_gen_conversation_direction())
        direction_step.add_done_callback(self.on_direction_ret_complete)

    def on_direction_ret_complete(self, fut: Future):
        direction_ret = fut.result()

        direction = direction_ret['_retrieve_gen_conversation_direction']['conversation_direction']

        logging.info('conversation direction: %s', direction)  # We will be using this later for anticipatory retrieval

        analyze_step = self.service.submit_async_tasks(self._analyze_prompt(), self._generate_indicies())

        analyze_step.add_done_callback(self.on_analyze_complete)

    def on_analyze_complete(self, fut: Future):
        try:
            prompt = fut.result()  # This will raise an exception if the coroutine fails
            logging.info('Prompt: %s', prompt)

            query_index_db_future = self.service.submit_async_tasks(self._query_index_db())

            query_index_db_future.add_done_callback(self.on_query_index_db)

        except Exception:
            logging.exception('Error in analyzing prompt.')

    def on_query_index_db(self, fut: Future):
        try:
            set_ret = fut.result()
            logging.info('Query Result: %s', set_ret['_query_index_db'])
        except Exception:
            logging.exception('Error in querying index DB.')

    async def _retrieve_gen_conversation_direction(self):
        plugin = self.retrieve_gen_conversation_direction_plugin
        # add prompt engineering here and submit as the full prompt.
        ret = plugin['func'].submit(prompt=self.prompt, args=plugin['args'])
        return ret[0]

    async def _analyze_prompt(self):
        plugin = self.prompt_analysis_plugin
        # add prompt engineering here and submit as the full prompt.
        ret = plugin['func'].submit(prompt=self.prompt, args=plugin['args'])
        return ret[0]

    async def _generate_indicies(self):
        plugin = self.prompt_retrieve_indicies_plugin
        # add prompt engineering here and submit as the full prompt.
        ret = plugin['func'].submit(prompt=self.prompt, args=plugin['args'])
        return ret[0]

    async def _query_index_db(self):
        plugin = self.prompt_query_index_db_plugin
        # add prompt engineering here and submit as the full prompt.
        ret = plugin['func'].query(prompt=self.prompt, args=plugin['args'])
        return ret[0]
