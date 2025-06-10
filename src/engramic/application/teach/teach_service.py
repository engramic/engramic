# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

"""
Provides services for generating educational content and lessons from documents.
"""

import uuid
from typing import Any

from engramic.application.teach.lesson import Lesson
from engramic.core.host import Host
from engramic.core.meta import Meta
from engramic.infrastructure.system.service import Service


class TeachService(Service):
    """
    Service that generates educational lessons from documents.

    Monitors document insertions and metadata completion to create learning
    materials based on document content.

    Attributes:
        teach_generate_questions: Plugin for generating questions from documents.
        meta_cache (dict[str, Meta]): Cache for document metadata.

    Methods:
        init_async() -> None:
            Initializes asynchronous components.
        start() -> None:
            Starts the service and subscribes to relevant topics.
        on_meta_complete(msg) -> None:
            Handles metadata completion events.
        on_document_inserted(msg) -> None:
            Processes newly inserted documents to create lessons.
    """

    def __init__(self, host: Host) -> None:
        """
        Initializes the TeachService.

        Args:
            host (Host): The host system providing access to plugins and services.
        """
        super().__init__(host)
        self.teach_generate_questions = host.plugin_manager.get_plugin('llm', 'teach_generate_questions')
        self.meta_cache: dict[str, Meta] = {}

    def init_async(self) -> None:
        """Initializes asynchronous components of the service."""
        return super().init_async()

    def start(self) -> None:
        """
        Starts the service and subscribes to relevant topics.

        Subscribes to META_COMPLETE and DOCUMENT_INSERTED topics to monitor
        document processing events.
        """
        self.subscribe(Service.Topic.META_COMPLETE, self.on_meta_complete)
        self.subscribe(Service.Topic.DOCUMENT_INSERTED, self.on_document_inserted)
        super().start()

    def on_meta_complete(self, msg: dict[Any, Any]) -> None:
        """
        Handles metadata completion events.

        Stores document metadata in the cache for later processing.

        Args:
            msg (dict[Any, Any]): The metadata message.
        """
        meta = Meta(**msg)
        if meta.type == meta.SourceType.DOCUMENT.value and meta.parent_id is not None:
            self.meta_cache[meta.parent_id] = meta

    def on_document_inserted(self, msg: dict[Any, Any]) -> None:
        """
        Processes newly inserted documents to create lessons.

        When a document is inserted and its metadata is available, creates
        a new lesson for the document.

        Args:
            msg (dict[Any, Any]): The document insertion message.
        """
        document_id = msg['id']
        if document_id in self.meta_cache:
            meta = self.meta_cache[document_id]
            lesson = Lesson(self, str(uuid.uuid4()), str(uuid.uuid4()), document_id)
            lesson.run_lesson(meta)
            del self.meta_cache[document_id]
