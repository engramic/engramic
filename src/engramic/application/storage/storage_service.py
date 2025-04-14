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
    A service responsible for persisting various data artifacts generated during the Engramic runtime process.

    The StorageService listens to multiple system topics and asynchronously saves different types of data,
    including observations, engrams, metadata, and history responses. It utilizes plugin-based repositories
    for storage and maintains metrics on saved entities for monitoring and reporting.

    Attributes:
        plugin_manager (PluginManager): Manages system plugins including the database plugin.
        db_document_plugin: The database document plugin used by repositories.
        history_repository (HistoryRepository): Handles persistence of history data.
        observation_repository (ObservationRepository): Handles persistence of observations.
        engram_repository (EngramRepository): Handles persistence of engrams.
        meta_repository (MetaRepository): Handles persistence of metadata.
        metrics_tracker (MetricsTracker): Tracks and reports storage metrics for each saved entity type.

    Methods:
        start(): Subscribes to message topics and prepares the service for operation.
        init_async(): Initializes database connections asynchronously.
        on_engram_complete(engram_dict): Callback to handle completed engrams and trigger storage.
        on_observation_complete(response): Callback to handle completed observations and trigger storage.
        on_prompt_complete(response_dict): Callback to handle completed prompt responses and trigger history storage.
        on_meta_complete(meta_dict): Callback to handle completed meta information and trigger storage.
        save_observation(response): Asynchronously saves an observation and updates metrics.
        save_history(response): Asynchronously saves a history response and updates metrics.
        save_engram(engram): Asynchronously saves an engram and updates metrics.
        save_meta(meta): Asynchronously saves meta information and updates metrics.
        on_acknowledge(message_in): Collects metrics and sends a status update on acknowledgment.
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
