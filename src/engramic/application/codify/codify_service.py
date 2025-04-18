# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import asyncio
import logging
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
    from engramic.core.observation import Observation
    from engramic.infrastructure.system.plugin_manager import PluginManager


class CodifyMetric(Enum):
    RESPONSE_RECIEVED = 'response_recieved'
    ENGRAM_FETCHED = 'engram_fetched'
    ENGRAM_VALIDATED = 'engram_validated'


class CodifyService(Service):
    """
    CodifyService is a system-level service responsible for validating and extracting engrams (memories) from AI model responses using a TOML-based validation pipeline.

    This service listens for prompts that have completed processing, and if the system is in training mode, it fetches related engrams and metadata, applies an LLM-based validation process, and stores structured observations. It tracks metrics related to its activity and supports training workflows.

    Key Responsibilities:
    - Subscribes to relevant service events like `MAIN_PROMPT_COMPLETE` and `ACKNOWLEDGE`.
    - Fetches engrams and their associated metadata based on a completed model response.
    - Uses a validation plugin to process model responses and extract structured observation data.
    - Validates and loads TOML-encoded responses into structured Observation objects.
    - Merges observations when applicable and sends results asynchronously to downstream systems.
    - Tracks system-level metrics for observability and debugging.

    Attributes:
        plugin_manager (PluginManager): Manages access to system plugins such as the LLM and document DB.
        engram_repository (EngramRepository): Repository for accessing and managing engram data.
        meta_repository (MetaRepository): Repository for associated metadata retrieval.
        observation_repository (ObservationRepository): Handles validation and normalization of observation data.
        prompt (Prompt): Default prompt object used during validation.
        metrics_tracker (MetricsTracker): Tracks custom CodifyMetric metrics.
        training_mode (bool): Flag indicating whether the system is in training mode.

    Methods:
        start(): Subscribes the service to key topics.
        stop(): Stops the service.
        init_async(): Initializes async components, including DB connections.
        on_set_training_mode(message_in): Sets training mode flag based on incoming message.
        on_main_prompt_complete(response_dict): Main entry point triggered after a model completes a prompt.
        fetch_engrams(response): Asynchronously fetches engrams associated with a response.
        on_fetch_engram_complete(fut): Callback that processes fetched engrams and triggers metadata retrieval.
        fetch_meta(engram_array, meta_id_array, response): Asynchronously fetches metadata for given engrams.
        on_fetch_meta_complete(fut): Callback that begins the validation process after fetching metadata.
        validate(engram_array, meta_array, response): Runs the validation plugin on the response and returns an observation.
        on_validate_complete(fut): Final step that emits the completed observation to other systems.
        on_acknowledge(message_in): Responds to ACK messages by reporting and resetting metrics.
    """

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
        self.training_mode = False

    def start(self) -> None:
        self.subscribe(Service.Topic.ACKNOWLEDGE, self.on_acknowledge)
        self.subscribe(Service.Topic.MAIN_PROMPT_COMPLETE, self.on_main_prompt_complete)
        self.subscribe(Service.Topic.SET_TRAINING_MODE, self.on_set_training_mode)
        super().start()

    async def stop(self) -> None:
        await super().stop()

    def init_async(self) -> None:
        self.db_document_plugin['func'].connect(args=None)
        return super().init_async()

    def on_set_training_mode(self, message_in: dict[str, Any]) -> None:
        self.training_mode = message_in['training_mode']

    def on_main_prompt_complete(self, response_dict: dict[str, Any]) -> None:
        if __debug__:
            self.host.update_mock_data_input(self, response_dict)

        if not self.training_mode:
            return

        prompt_str = response_dict['prompt_str']
        model = response_dict['model']
        analysis = PromptAnalysis(**response_dict['analysis'])
        retrieve_result = RetrieveResult(**response_dict['retrieve_result'])
        response = Response(
            response_dict['id'], response_dict['response'], retrieve_result, prompt_str, analysis, model
        )
        self.metrics_tracker.increment(CodifyMetric.RESPONSE_RECIEVED)
        fetch_engram_step = self.run_task(self._fetch_engrams(response))
        fetch_engram_step.add_done_callback(self.on_fetch_engram_complete)

    """
    ### Fetch Engrams & Meta

    Fetch engrams based on retrieved results.
    """

    async def _fetch_engrams(self, response: Response) -> dict[str, Any]:
        engram_array: list[Engram] = await asyncio.to_thread(
            self.engram_repository.load_batch_retrieve_result, response.retrieve_result
        )

        self.metrics_tracker.increment(CodifyMetric.ENGRAM_FETCHED, len(engram_array))

        meta_array: set[str] = set()
        for engram in engram_array:
            if engram.meta_ids is not None:
                meta_array.update(engram.meta_ids)

        return {'engram_array': engram_array, 'meta_array': list(meta_array), 'response': response}

    def on_fetch_engram_complete(self, fut: Future[Any]) -> None:
        ret = fut.result()
        fetch_meta_step = self.run_task(self._fetch_meta(ret['engram_array'], ret['meta_array'], ret['response']))
        fetch_meta_step.add_done_callback(self.on_fetch_meta_complete)

    async def _fetch_meta(
        self, engram_array: list[Engram], meta_id_array: list[str], response: Response
    ) -> dict[str, Any]:
        meta_array: list[Meta] = await asyncio.to_thread(self.meta_repository.load_batch, meta_id_array)
        # assembled main_prompt, render engrams.
        return {'engram_array': engram_array, 'meta_array': meta_array, 'response': response}

    def on_fetch_meta_complete(self, fut: Future[Any]) -> None:
        ret = fut.result()
        fetch_meta_step = self.run_task(self._validate(ret['engram_array'], ret['meta_array'], ret['response']))
        fetch_meta_step.add_done_callback(self.on_validate_complete)

    """
    ### Validate

    Validates and extracts engrams (i.e. memories) from responses.
    """

    async def _validate(self, engram_array: list[Engram], meta_array: list[Meta], response: Response) -> dict[str, Any]:
        # insert prompt engineering

        del meta_array

        input_data = {
            'engram_list': engram_array,
            'response': response.response,
        }

        prompt = PromptValidatePrompt(response.prompt_str, input_data=input_data)

        plugin = self.llm_validate
        validate_response = await asyncio.to_thread(
            plugin['func'].submit, prompt=prompt, structured_schema=None, args=self.host.mock_update_args(plugin)
        )

        self.host.update_mock_data(self.llm_validate, validate_response)

        toml_data = None

        try:
            if __debug__:
                prompt_render = prompt.render_prompt()
                self.send_message_async(
                    Service.Topic.DEBUG_OBSERVATION_TOML_COMPLETE,
                    {'prompt': prompt_render, 'toml': validate_response[0]['llm_response'], 'response_id': response.id},
                )

            toml_data = tomli.loads(validate_response[0]['llm_response'])

        except tomli.TOMLDecodeError as e:
            logging.exception('TOML decode error: %s', validate_response[0]['llm_response'])
            error = 'Malformed TOML file in codify:validate.'
            raise TypeError(error) from e

        if 'not_memorable' in toml_data:
            return {'return_observation': None}

        if not self.observation_repository.validate_toml_dict(toml_data):
            error = 'Codify TOML did not pass validation.'
            raise TypeError(error)

        return_observation = self.observation_repository.load_toml_dict(
            self.observation_repository.normalize_toml_dict(toml_data, response)
        )

        # if this observation is from multiple sources, it must be merged the sources into it's meta.
        if len(engram_array) > 0:
            return_observation_merged: Observation = return_observation.merge_observation(
                return_observation,
                CodifyService.ACCURACY_CONSTANT,
                CodifyService.RELEVANCY_CONSTANT,
                self.engram_repository,
            )

            return {'return_observation': return_observation_merged}

        self.metrics_tracker.increment(CodifyMetric.ENGRAM_VALIDATED)

        return {'return_observation': return_observation}

    def on_validate_complete(self, fut: Future[Any]) -> None:
        ret = fut.result()

        if ret['return_observation'] is not None:
            self.send_message_async(Service.Topic.OBSERVATION_COMPLETE, asdict(ret['return_observation']))

        if __debug__:
            self.host.update_mock_data_output(self, asdict(ret['return_observation']))

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
