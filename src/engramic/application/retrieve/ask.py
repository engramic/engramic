# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import logging

from concurrent.futures import Future
from engramic.core import Library, Prompt, Retrieval
from engramic.infrastructure.system.service import Service
from engramic.infrastructure.system.plugin_manager import PluginManager



class Ask(Retrieval):
    def __init__(self, prompt: Prompt,plugin_manager:PluginManager, library:Library=None,) -> None:
        self.service = None
        self.library = library
        self.prompt = prompt
        self.prompt_analysis_plugin = plugin_manager.get_plugin("llm","retrieve_prompt_analysis")
        self.prompt_retrieve_indicies_plugin = plugin_manager.get_plugin("llm","retrieve_gen_index")
        self.prompt_query_index_db_plugin = plugin_manager.get_plugin("vector_db","query")
        var = 0
        

    def get_sources(self, service: Service) -> None:
        analyze_step = service.submit_async_tasks(self._analyze_prompt(), self._generate_indicies())

        def on_analyze_complete(fut: Future):
            try:
                prompt = fut.result()  # This will raise an exception if the coroutine fails
                logging.info('Prompt: %s', prompt)

                query_index_db_future = service.submit_async_tasks(self._query_index_db())

                def on_query_index_db(fut: Future):
                    try:
                        set_ret = fut.result()
                        logging.info('Query Result: %s', set_ret["_query_index_db"])
                    except Exception as e:
                        logging.error(f"Error in querying index DB: {e}")

                query_index_db_future.add_done_callback(on_query_index_db)

            except Exception as e:
                logging.error(f"Error in analyzing prompt: {e}")

        analyze_step.add_done_callback(on_analyze_complete)



    async def _analyze_prompt(self):
        plugin = self.prompt_analysis_plugin
        ret = plugin.submit(prompt=self.prompt)
        return ret[0]


    async def _generate_indicies(self):
        plugin = self.prompt_retrieve_indicies_plugin
        ret = plugin.submit(prompt=self.prompt)
        return ret[0]


    async def _query_index_db(self):
        plugin = self.prompt_query_index_db_plugin
        ret = plugin.query(prompt=self.prompt)
        return ret[0]
