# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import asyncio
import time
import uuid
from enum import Enum
from typing import TYPE_CHECKING, Any

from engramic.application.retrieve.ask import Ask
from engramic.core import Index, Meta, Prompt
from engramic.core.host import Host
from engramic.core.metrics_tracker import MetricPacket, MetricsTracker
from engramic.infrastructure.repository.meta_repository import MetaRepository
from engramic.infrastructure.system.service import Service

if TYPE_CHECKING:
    from engramic.infrastructure.system.plugin_manager import PluginManager


class RetrieveMetric(Enum):
    PROMPTS_SUBMITTED = 'prompts_submitted'
    EMBEDDINGS_ADDED_TO_VECTOR = 'embeddings_added_to_vector'
    META_ADDED_TO_VECTOR = 'meta_added_to_vector'
    CONVERSATION_DIRECTION_CALCULATED = 'conversation_direction_calculated'
    PROMPTS_ANALYZED = 'prompts_analyzed'
    DYNAMIC_INDICES_GENERATED = 'dynamic_indices_generated'
    VECTOR_DB_QUERIES = 'vector_db_queries'


class RetrieveService(Service):
    """
    Service responsible for handling semantic prompt retrieval. It communicates with vector and document databases via plugins and tracks operational metrics for observability.

    Attributes:
        plugin_manager (PluginManager): Plugin manager to access database and vector services.
        vector_db_plugin (dict): Plugin for interacting with the vector database.
        db_plugin (dict): Plugin for document database operations.
        metrics_tracker (MetricsTracker): Tracks various retrieval-related metrics.
        meta_repository (MetaRepository): Handles persistence and loading of Meta objects.

    Methods:
        init_async(): Initializes the database connection.
        start(): Subscribes to service topics for prompt submission, indexing, and metadata completion.
        stop(): Stops the service and cleans up subscriptions.

        submit(prompt): Initiates the retrieval process for a given prompt and logs metrics.
        on_submit_prompt(data): Handles incoming prompt strings from messaging, wraps them in a Prompt object, and triggers retrieval.

        on_index_complete(index_message): Callback that handles completed indices and submits them to the vector DB.
        on_meta_complete(meta_dict): Callback for completed metadata, converts and submits to vector DB.

        insert_meta_vector(meta): Asynchronously inserts metadata summaries into the vector DB.
        insert_engram_vector(index_list, engram_id): Asynchronously inserts semantic indices into the vector DB.

        on_acknowledge(message_in): Handles status reporting and resets the current metric tracker.
    """

    def __init__(self, host: Host) -> None:
        super().__init__(host)
        self.plugin_manager: PluginManager = host.plugin_manager
        self.vector_db_plugin = host.plugin_manager.get_plugin('vector_db', 'db')
        self.db_plugin = host.plugin_manager.get_plugin('db', 'document')
        self.metrics_tracker: MetricsTracker[RetrieveMetric] = MetricsTracker[RetrieveMetric]()
        self.meta_repository: MetaRepository = MetaRepository(self.db_plugin)

    def init_async(self) -> None:
        self.db_plugin['func'].connect(args=None)
        return super().init_async()

    def start(self) -> None:
        self.subscribe(Service.Topic.ACKNOWLEDGE, self.on_acknowledge)
        self.subscribe(Service.Topic.SUBMIT_PROMPT, self.on_submit_prompt)
        self.subscribe(Service.Topic.INDEX_COMPLETE, self.on_index_complete)
        self.subscribe(Service.Topic.META_COMPLETE, self.on_meta_complete)

    def stop(self) -> None:
        super().stop()

    # when called from monitor service
    def on_submit_prompt(self, data: str) -> None:
        self.submit(Prompt(data))

    # when used from main
    def submit(self, prompt: Prompt) -> None:
        self.metrics_tracker.increment(RetrieveMetric.PROMPTS_SUBMITTED)
        retrieval = Ask(str(uuid.uuid4()), prompt, self.plugin_manager, self.metrics_tracker, self.db_plugin, self)
        retrieval.get_sources()

    def on_index_complete(self, index_message: dict[str, Any]) -> None:
        raw_index: list[dict[str, Any]] = index_message['index']
        engram_id: str = index_message['engram_id']
        index_list: list[Index] = [Index(**item) for item in raw_index]
        self.run_task(self.insert_engram_vector(index_list, engram_id))

    async def insert_engram_vector(self, index_list: list[Index], engram_id: str) -> None:
        plugin = self.vector_db_plugin
        self.vector_db_plugin['func'].insert(
            collection_name='main', index_list=index_list, obj_id=engram_id, args=plugin['args']
        )

        self.host.write_mock_data()
        self.metrics_tracker.increment(RetrieveMetric.EMBEDDINGS_ADDED_TO_VECTOR)

    def on_meta_complete(self, meta_dict: dict[str, Any]) -> None:
        meta = self.meta_repository.load(meta_dict)
        self.run_task(self.insert_meta_vector(meta))
        self.metrics_tracker.increment(RetrieveMetric.META_ADDED_TO_VECTOR)

    async def insert_meta_vector(self, meta: Meta) -> None:
        plugin = self.vector_db_plugin
        await asyncio.to_thread(
            self.vector_db_plugin['func'].insert,
            collection_name='meta',
            index_list=[meta.summary_full],
            obj_id=meta.id,
            args=plugin['args'],
        )

    def on_acknowledge(self, message_in: str) -> None:
        del message_in

        metrics_packet: MetricPacket = self.metrics_tracker.get_and_reset_packet()

        self.send_message_async(
            Service.Topic.STATUS,
            {'id': self.id, 'name': self.__class__.__name__, 'timestamp': time.time(), 'metrics': metrics_packet},
        )
