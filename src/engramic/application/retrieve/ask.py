# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import logging

from concurrent.futures import Future
from engramic.core import Library, Prompt, Retrieval
from engramic.infrastructure.system.service import Service


class Ask(Retrieval):
    def __init__(self, prompt: Prompt,library:Library=None) -> None:
        self.service = None
        self.library = library
        self.prompt = prompt

    def get_sources(self, service: Service) -> Retrieval.RetrievalResponse:
    
        analyze_step = service.submit_async_tasks(self._analyze_prompt(),self._generate_indicies())

        def on_analyze_complete(fut: Future):
            if analyze_step.done():
                prompt = analyze_step.result()
                logging.info('Prompt: %s', prompt)

                query_index_db_future = service.submit_async_tasks(self._query_index_db())

                def on_query_index_db(fut: Future):
                    if query_index_db_future.done():
                        set_ret = query_index_db_future.result()
                        logging.info('Query Result: %s', set_ret["_query_index_db"].set)

                query_index_db_future.add_done_callback(on_query_index_db)

        analyze_step.add_done_callback(on_analyze_complete)


    @staticmethod
    async def _analyze_prompt():
        return 'test'

    @staticmethod
    async def _generate_indicies():
        return 'test'

    @staticmethod
    async def _query_index_db():
        return Retrieval.RetrievalResponse([1, 2, 3])
