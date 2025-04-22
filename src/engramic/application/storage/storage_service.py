# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import asyncio
import logging
import time
from enum import Enum
from typing import TYPE_CHECKING, Any

from engramic.core import Engram, Meta, Response
from engramic.core.host import Host
from engramic.core.metrics_tracker import MetricPacket, MetricsTracker
from engramic.core.observation import Observation
from engramic.infrastructure.repository.engram_repository import EngramRepository
from engramic.infrastructure.repository.history_repository import HistoryRepository
from engramic.infrastructure.repository.meta_repository import MetaRepository
from engramic.infrastructure.repository.observation_repository import ObservationRepository
from engramic.infrastructure.system.plugin_manager import PluginManager
from engramic.infrastructure.system.service import Service

if TYPE_CHECKING:
    from engramic.infrastructure.system.plugin_manager import PluginManager


class StorageMetric(Enum):
    OBSERVATION_SAVED = 'observation_saved'
    ENGRAM_SAVED = 'engram_saved'
    META_SAVED = 'meta_saved'
    HISTORY_SAVED = 'history_saved'


class StorageService(Service):
    """
    A service responsible for persisting runtime data artifacts within the Engramic system.

    StorageService listens for various system events and saves corresponding data—including observations,
    engrams, metadata, and prompt histories—via plugin-based repositories. It also tracks metrics for each
    type of saved entity to facilitate performance monitoring and operational insights.

    Attributes:
        plugin_manager (PluginManager): Provides access to system plugins, including database integrations.
        db_document_plugin: Plugin used by repositories for data persistence.
        history_repository (HistoryRepository): Manages saving of prompt/response history data.
        observation_repository (ObservationRepository): Handles saving of Observation entities.
        engram_repository (EngramRepository): Handles saving of Engram entities.
        meta_repository (MetaRepository): Handles saving of Meta configuration entities.
        metrics_tracker (MetricsTracker): Tracks counts of saved items for metric reporting.

    Methods:
        start(): Registers the service to relevant message topics and begins operation.
        init_async(): Connects to the database plugin asynchronously before full service startup.
        on_engram_complete(engram_dict): Callback for storing completed engram batches.
        on_observation_complete(response): Callback for storing completed observations.
        on_prompt_complete(response_dict): Callback for storing completed prompt/response history.
        on_meta_complete(meta_dict): Callback for storing finalized meta configuration.
        save_observation(response): Coroutine to persist observations and update metrics.
        save_history(response): Coroutine to persist prompt/response history and update metrics.
        save_engram(engram): Coroutine to persist engram data and update metrics.
        save_meta(meta): Coroutine to persist metadata and update metrics.
        on_acknowledge(message_in): Collects current metrics and publishes service status.
    """

    def __init__(self, host: Host) -> None:
        super().__init__(host)
        self.plugin_manager: PluginManager = host.plugin_manager
        self.db_document_plugin = self.plugin_manager.get_plugin('db', 'document')
        self.history_repository: HistoryRepository = HistoryRepository(self.db_document_plugin)
        self.observation_repository: ObservationRepository = ObservationRepository(self.db_document_plugin)
        self.engram_repository: EngramRepository = EngramRepository(self.db_document_plugin)
        self.meta_repository: MetaRepository = MetaRepository(self.db_document_plugin)
        self.metrics_tracker: MetricsTracker[StorageMetric] = MetricsTracker[StorageMetric]()

    def start(self) -> None:
        self.subscribe(Service.Topic.ACKNOWLEDGE, self.on_acknowledge)
        self.subscribe(Service.Topic.MAIN_PROMPT_COMPLETE, self.on_prompt_complete)
        self.subscribe(Service.Topic.OBSERVATION_COMPLETE, self.on_observation_complete)
        self.subscribe(Service.Topic.ENGRAM_COMPLETE, self.on_engram_complete)
        self.subscribe(Service.Topic.META_COMPLETE, self.on_meta_complete)
        super().start()

    def init_async(self) -> None:
        self.db_document_plugin['func'].connect(args=None)
        return super().init_async()

    def on_engram_complete(self, engram_dict: dict[str, Any]) -> None:
        engram_batch = self.engram_repository.load_batch_dict(engram_dict['engram_array'])
        for engram in engram_batch:
            self.run_task(self.save_engram(engram))

    def on_observation_complete(self, response: Observation) -> None:
        self.run_task(self.save_observation(response))

    def on_prompt_complete(self, response_dict: dict[Any, Any]) -> None:
        response = Response(**response_dict)
        self.run_task(self.save_history(response))

    def on_meta_complete(self, meta_dict: dict[str, str]) -> None:
        meta: Meta = self.meta_repository.load(meta_dict)
        self.run_task(self.save_meta(meta))

    async def save_observation(self, response: Observation) -> None:
        self.observation_repository.save(response)
        self.metrics_tracker.increment(StorageMetric.OBSERVATION_SAVED)
        logging.debug('Storage service saving observation.')

    async def save_history(self, response: Response) -> None:
        await asyncio.to_thread(self.history_repository.save_history, response)
        self.metrics_tracker.increment(StorageMetric.HISTORY_SAVED)
        logging.debug('Storage service saving history.')

    async def save_engram(self, engram: Engram) -> None:
        await asyncio.to_thread(self.engram_repository.save_engram, engram)
        self.metrics_tracker.increment(StorageMetric.ENGRAM_SAVED)
        logging.debug('Storage service saving engram.')

    async def save_meta(self, meta: Meta) -> None:
        logging.debug('Storage service saving meta.')
        await asyncio.to_thread(self.meta_repository.save, meta)
        self.metrics_tracker.increment(StorageMetric.META_SAVED)

    def on_acknowledge(self, message_in: str) -> None:
        del message_in

        metrics_packet: MetricPacket = self.metrics_tracker.get_and_reset_packet()

        self.send_message_async(
            Service.Topic.STATUS,
            {'id': self.id, 'name': self.__class__.__name__, 'timestamp': time.time(), 'metrics': metrics_packet},
        )
