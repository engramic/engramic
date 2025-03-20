# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import logging
from dataclasses import asdict
from typing import TYPE_CHECKING, Any

import tomli

from engramic.core import Engram, Meta, Prompt, PromptAnalysis
from engramic.core.response import Response
from engramic.core.retrieve_result import RetrieveResult
from engramic.infrastructure.repository.engram_repository import EngramRepository
from engramic.infrastructure.repository.meta_repository import MetaRepository
from engramic.infrastructure.repository.observation_repository import ObservationRepository
from engramic.infrastructure.system.host import Host
from engramic.infrastructure.system.plugin_manager import PluginManager
from engramic.infrastructure.system.service import Service

if TYPE_CHECKING:
    from engramic.infrastructure.system.plugin_manager import PluginManager


class CodifyService(Service):
    def __init__(self, host: Host) -> None:
        super().__init__(host)
        self.plugin_manager: PluginManager = host.plugin_manager
        self.engram_repository: EngramRepository = EngramRepository(self.plugin_manager)
        self.meta_repository: MetaRepository = MetaRepository(self.plugin_manager)
        self.observation_repository: ObservationRepository = ObservationRepository(self.plugin_manager)
        self.llm_validate = self.plugin_manager.get_plugin('llm', 'validate')
        self.prompt = Prompt('Validate the llm.')

    def start(self) -> None:
        self.subscribe(Service.Topic.MAIN_PROMPT_COMPLETE, self.on_prompt_complete)

    def on_prompt_complete(self, response_dict: dict[str, Any]) -> None:
        prompt = Prompt(response_dict['prompt'])
        analysis = PromptAnalysis(**response_dict['analysis'])
        retrieve_result = RetrieveResult(**response_dict['retrieve_result'])
        response = Response(response_dict['id'], response_dict['response'], retrieve_result, prompt, analysis)
        self.run_task(self.fetch_engrams(response))

    async def validate(self, engram_array: list[Engram], meta_array: list[Meta], response: Response) -> None:
        # insert prompt engineering
        del engram_array
        del meta_array
        del response

        mock_response = self.llm_validate['func'].submit(prompt=self.prompt, args=self.llm_validate['args'])

        memories = tomli.loads(mock_response[0]['llm_response'])
        observation = self.observation_repository.load_toml_file(memories)

        logging.info('Codify complete. %s', observation.meta)

        self.send_message_async(Service.Topic.CODIFY_COMPLETE, asdict(observation))

    async def fetch_meta(self, engram_array: list[Engram], meta_id_array: list[str], response: Response) -> None:
        meta_array: list[Meta] = self.meta_repository.load_batch(meta_id_array)
        # assembled main_prompt, render engrams.
        self.run_task(self.validate(engram_array, meta_array, response))

    async def fetch_engrams(self, response: Response) -> None:
        engram_array: list[Engram] = self.engram_repository.load_batch_retrieve_result(response.retrieve_result)

        meta_array: list[str] = []
        for engram in engram_array:
            if engram.meta_ids is not None:
                meta_array.extend(engram.meta_ids)

        self.run_task(self.fetch_meta(engram_array, meta_array, response))
