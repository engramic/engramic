# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import asyncio
import time
import uuid
from dataclasses import asdict
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
    Manages semantic prompt retrieval and indexing by coordinating between vector/document databases,
    tracking metrics, and responding to system events.

    This service is responsible for receiving prompt submissions, retrieving relevant information using
    vector similarity, and handling the indexing and metadata enrichment process. It interfaces with
    plugin-managed databases and provides observability through metrics tracking.

    Attributes:
        plugin_manager (PluginManager): Access point for system plugins, including vector and document DBs.
        vector_db_plugin (dict): Plugin used for vector database operations (e.g., semantic search).
        db_plugin (dict): Plugin for interacting with the document database.
        metrics_tracker (MetricsTracker): Collects and resets retrieval-related metrics for monitoring.
        meta_repository (MetaRepository): Handles Meta object persistence and transformation.
        repo_folders (dict[str, Any]): Dictionary containing repository folder information.

    Methods:
        init_async(): Initializes database connections and plugin setup asynchronously.
        start(): Subscribes to system topics for prompt processing and indexing lifecycle.
        stop(): Cleans up the service and halts processing.

        submit(prompt: Prompt): Begins the retrieval process and logs submission metrics.
        on_submit_prompt(msg: dict[Any, Any]): Processes a prompt message and submits for processing.
        _on_repo_folders(msg: dict[str, Any]): Updates repository folder information.

        on_indices_complete(index_message: dict): Converts index payload into Index objects and queues for insertion.
        _insert_engram_vector(index_list: list[Index], engram_id: str, repo_ids: str, tracking_id: str):
            Asynchronously inserts semantic indices into vector DB with repository filters.

        on_meta_complete(meta_dict: dict): Loads and inserts metadata summary into the vector DB.
        insert_meta_vector(meta: Meta): Runs metadata vector insertion in a background thread.

        on_acknowledge(message_in: str): Emits service metrics to the status channel and resets the tracker.
    """

    def __init__(self, host: Host) -> None:
        super().__init__(host)

        self.plugin_manager: PluginManager = host.plugin_manager
        self.vector_db_plugin = host.plugin_manager.get_plugin('vector_db', 'db')
        self.db_plugin = host.plugin_manager.get_plugin('db', 'document')
        self.metrics_tracker: MetricsTracker[RetrieveMetric] = MetricsTracker[RetrieveMetric]()
        self.meta_repository: MetaRepository = MetaRepository(self.db_plugin)
        self.repo_folders: dict[str, Any] = {}

    def init_async(self) -> None:
        self.db_plugin['func'].connect(args=None)
        return super().init_async()

    def start(self) -> None:
        self.subscribe(Service.Topic.ACKNOWLEDGE, self.on_acknowledge)
        self.subscribe(Service.Topic.SUBMIT_PROMPT, self.on_submit_prompt)
        self.subscribe(Service.Topic.INDICES_COMPLETE, self.on_indices_complete)
        self.subscribe(Service.Topic.META_COMPLETE, self.on_meta_complete)
        self.subscribe(Service.Topic.REPO_FOLDERS, self._on_repo_folders)
        super().start()

    async def stop(self) -> None:
        await super().stop()

    def _on_repo_folders(self, msg: dict[str, Any]) -> None:
        self.repo_folders = msg['repo_folders']

    # when called from monitor service
    def on_submit_prompt(self, msg: dict[Any, Any]) -> None:
        self.submit(Prompt(**msg))

    # when used from main
    def submit(self, prompt: Prompt) -> None:
        if __debug__:
            self.host.update_mock_data_input(self, asdict(prompt))

        self.metrics_tracker.increment(RetrieveMetric.PROMPTS_SUBMITTED)
        retrieval = Ask(str(uuid.uuid4()), prompt, self.plugin_manager, self.metrics_tracker, self.db_plugin, self)
        retrieval.get_sources()

        async def send_message() -> None:
            msg = {'id': prompt.prompt_id, 'parent_id': prompt.parent_id, 'tracking_id': prompt.tracking_id}
            self.send_message_async(Service.Topic.PROMPT_CREATED, msg)

        self.run_task(send_message())

    def on_indices_complete(self, index_message: dict[str, Any]) -> None:
        raw_index: list[dict[str, Any]] = index_message['index']
        engram_id: str = index_message['engram_id']
        tracking_id: str = index_message['tracking_id']
        repo_ids: str = index_message['repo_ids']
        index_list: list[Index] = [Index(**item) for item in raw_index]
        self.run_task(self._insert_engram_vector(index_list, engram_id, repo_ids, tracking_id))

    async def _insert_engram_vector(
        self, index_list: list[Index], engram_id: str, repo_ids: str, tracking_id: str
    ) -> None:
        plugin = self.vector_db_plugin
        self.vector_db_plugin['func'].insert(
            collection_name='main', index_list=index_list, obj_id=engram_id, args=plugin['args'], filters=repo_ids
        )

        index_id_array = [index.id for index in index_list]

        self.send_message_async(
            Service.Topic.INDICES_INSERTED,
            {'parent_id': engram_id, 'index_id_array': index_id_array, 'tracking_id': tracking_id},
        )

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
            filters=meta.repo_ids,
            args=plugin['args'],
        )

    def on_acknowledge(self, message_in: str) -> None:
        del message_in

        metrics_packet: MetricPacket = self.metrics_tracker.get_and_reset_packet()

        self.send_message_async(
            Service.Topic.STATUS,
            {'id': self.id, 'name': self.__class__.__name__, 'timestamp': time.time(), 'metrics': metrics_packet},
        )
