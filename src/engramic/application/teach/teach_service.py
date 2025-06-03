# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import uuid
from typing import Any

from engramic.application.teach.lesson import Lesson
from engramic.core.host import Host
from engramic.core.meta import Meta
from engramic.infrastructure.system.service import Service


class TeachService(Service):
    def __init__(self, host: Host) -> None:
        super().__init__(host)
        self.teach_generate_questions = host.plugin_manager.get_plugin('llm', 'teach_generate_questions')
        self.meta_cache: dict[str, Meta] = {}

    def init_async(self) -> None:
        return super().init_async()

    def start(self) -> None:
        self.subscribe(Service.Topic.META_COMPLETE, self.on_meta_complete)
        self.subscribe(Service.Topic.DOCUMENT_INSERTED, self.on_document_inserted)
        super().start()

    def on_meta_complete(self, msg: dict[Any, Any]) -> None:
        meta = Meta(**msg)
        if meta.type == meta.SourceType.DOCUMENT.value and meta.parent_id is not None:
            self.meta_cache[meta.parent_id] = meta

    def on_document_inserted(self, msg: dict[Any, Any]) -> None:
        document_id = msg['id']
        if document_id in self.meta_cache:
            meta = self.meta_cache[document_id]
            lesson = Lesson(self, str(uuid.uuid4()), str(uuid.uuid4()), document_id)
            lesson.run_lesson(meta)
            del self.meta_cache[document_id]
