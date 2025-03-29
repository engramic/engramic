# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import time
from concurrent.futures import Future
from dataclasses import asdict
from enum import Enum
from typing import TYPE_CHECKING, Any

import tomli

from engramic.application.codify.prompt_validate_prompt import PromptValidatePrompt
from engramic.core import Engram, Meta, Prompt, PromptAnalysis
from engramic.core.host import Host
from engramic.core.metrics_tracker import MetricPacket, MetricsTracker
from engramic.core.response import Response
from engramic.core.retrieve_result import RetrieveResult
from engramic.infrastructure.repository.engram_repository import EngramRepository
from engramic.infrastructure.repository.meta_repository import MetaRepository
from engramic.infrastructure.repository.observation_repository import ObservationRepository
from engramic.infrastructure.system.plugin_manager import PluginManager
from engramic.infrastructure.system.service import Service

if TYPE_CHECKING:
    from engramic.infrastructure.system.plugin_manager import PluginManager


class CodifyMetric(Enum):
    RESPONSE_RECIEVED = 'response_recieved'
    ENGRAM_FETCHED = 'engram_fetched'
    ENGRAM_VALIDATED = 'engram_validated'


class CodifyService(Service):
    ACCURACY_CONSTANT = 3
    RELEVANCY_CONSTANT = 3

    def __init__(self, host: Host) -> None:
        super().__init__(host)
        self.plugin_manager: PluginManager = host.plugin_manager
        self.llm_validate = self.plugin_manager.get_plugin('llm', 'validate')
        self.db_document_plugin = self.plugin_manager.get_plugin('db', 'document')
        self.engram_repository: EngramRepository = EngramRepository(self.db_document_plugin)
        self.meta_repository: MetaRepository = MetaRepository(self.db_document_plugin)
        self.observation_repository: ObservationRepository = ObservationRepository(self.db_document_plugin)

        self.prompt = Prompt('Validate the llm.')
        self.metrics_tracker: MetricsTracker[CodifyMetric] = MetricsTracker[CodifyMetric]()
        self.training_mode = True

    def start(self) -> None:
        self.subscribe(Service.Topic.ACKNOWLEDGE, self.on_acknowledge)
        self.subscribe(Service.Topic.MAIN_PROMPT_COMPLETE, self.on_prompt_complete)

    def init_async(self) -> None:
        self.db_document_plugin['func'].connect()
        return super().init_async()

    def on_prompt_complete(self, response_dict: dict[str, Any]) -> None:
        if not self.training_mode:
            return

        prompt = Prompt(response_dict['prompt'])
        model = response_dict['model']
        analysis = PromptAnalysis(**response_dict['analysis'])
        retrieve_result = RetrieveResult(**response_dict['retrieve_result'])
        response = Response(response_dict['id'], response_dict['response'], retrieve_result, prompt, analysis, model)
        self.metrics_tracker.increment(CodifyMetric.RESPONSE_RECIEVED)
        fetch_engram_step = self.run_task(self.fetch_engrams(response))
        fetch_engram_step.add_done_callback(self.on_fetch_engram_complete)

    async def fetch_engrams(self, response: Response) -> dict[str, Any]:
        engram_array: list[Engram] = self.engram_repository.load_batch_retrieve_result(response.retrieve_result)

        self.metrics_tracker.increment(CodifyMetric.ENGRAM_FETCHED, len(engram_array))

        meta_array: set[str] = set()
        for engram in engram_array:
            if engram.meta_ids is not None:
                meta_array.add(engram.meta_ids[0])

        return {'engram_array': engram_array, 'meta_array': list(meta_array), 'response': response}

    def on_fetch_engram_complete(self, fut: Future[Any]) -> None:
        ret = fut.result()
        fetch_meta_step = self.run_task(self.fetch_meta(ret['engram_array'], ret['meta_array'], ret['response']))
        fetch_meta_step.add_done_callback(self.on_fetch_meta_complete)

    async def fetch_meta(
        self, engram_array: list[Engram], meta_id_array: list[str], response: Response
    ) -> dict[str, Any]:
        meta_array: list[Meta] = self.meta_repository.load_batch(meta_id_array)
        # assembled main_prompt, render engrams.
        return {'engram_array': engram_array, 'meta_array': meta_array, 'response': response}

    def on_fetch_meta_complete(self, fut: Future[Any]) -> None:
        ret = fut.result()
        fetch_meta_step = self.run_task(self.validate(ret['engram_array'], ret['meta_array'], ret['response']))
        fetch_meta_step.add_done_callback(self.on_validate_complete)

    async def validate(self, engram_array: list[Engram], meta_array: list[Meta], response: Response) -> dict[str, Any]:
        # insert prompt engineering

        del meta_array

        engram_list: list[Engram] = []
        for engram in engram_array:
            not_implemented = 'not implemented'
            raise NotImplementedError(not_implemented)
            engram_list.append(engram)

        input_data = {'engram_render_list': engram_list, 'response': response.response}

        prompt = PromptValidatePrompt(response.prompt.prompt_str, input_data=input_data)

        validate_response = self.llm_validate['func'].submit(
            prompt=prompt, structured_schema=None, args=self.llm_validate['args']
        )

        toml_data = tomli.loads(validate_response[0]['llm_response'])

        return_observation = self.observation_repository.load_toml_dict(
            self.observation_repository.normalize_toml_dict(toml_data, response)
        )

        # if this observation is from multiple sources, it must be merge the sources into it's meta.
        if len(engram_list) > 0:
            not_implemented = 'not implemented'
            raise NotImplementedError(not_implemented)
            # return_observation = observation.merge_observation(
            #    observation, CodifyService.ACCURACY_CONSTANT, CodifyService.RELEVANCY_CONSTANT, self.engram_repository
            # )

        self.metrics_tracker.increment(CodifyMetric.ENGRAM_VALIDATED)

        return {'return_observation': return_observation}

    def on_validate_complete(self, fut: Future[Any]) -> None:
        ret = fut.result()
        self.send_message_async(Service.Topic.OBSERVATION_COMPLETE, asdict(ret['return_observation']))

    def on_acknowledge(self, message_in: str) -> None:
        del message_in

        metrics_packet: MetricPacket = self.metrics_tracker.get_and_reset_packet()

        self.send_message_async(
            Service.Topic.STATUS,
            {'id': self.id, 'name': self.__class__.__name__, 'timestamp': time.time(), 'metrics': metrics_packet},
        )
