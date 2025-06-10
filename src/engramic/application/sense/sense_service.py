# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.
from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING, Any

from engramic.application.sense.scan import Scan
from engramic.core.document import Document
from engramic.infrastructure.system.service import Service

if TYPE_CHECKING:
    from concurrent.futures import Future

    from engramic.core.host import Host


class SenseService(Service):
    """
    Processes and analyzes documents to extract semantic content for the Engramic system.

    This service listens for document submission events, initializes a scan process that parses the media
    resource, and notifies the system of newly created inputs. Currently only supports document-based
    inputs, with other formats planned for future releases.

    Attributes:
        sense_initial_summary (Plugin): Plugin for generating an initial summary of the document.
        sense_scan_page (Plugin): Plugin for scanning and interpreting document content.
        sense_full_summary (Plugin): Plugin for producing full document summaries.

    Methods:
        init_async() -> None:
            Initializes the service asynchronously and sets up any required connections or state.
        start() -> None:
            Subscribes to the system topic for document submissions.
        on_document_submit(msg: dict[Any, Any]) -> None:
            Extracts file information from a message and submits the document.
        submit_document(document: Document, *, overwrite: bool = False) -> Document | None:
            Triggers scanning of the submitted document and sends async notification.
        on_document_created_sent(ret: Future[Any]) -> None:
            Callback function that initiates document scanning after creation notification.
    """

    def __init__(self, host: Host) -> None:
        super().__init__(host)
        self.sense_initial_summary = host.plugin_manager.get_plugin('llm', 'sense_initial_summary')
        self.sense_scan_page = host.plugin_manager.get_plugin('llm', 'sense_scan')
        self.sense_full_summary = host.plugin_manager.get_plugin('llm', 'sense_full_summary')

    def init_async(self) -> None:
        return super().init_async()

    def start(self) -> None:
        self.subscribe(Service.Topic.SUBMIT_DOCUMENT, self.on_document_submit)
        super().start()

    def on_document_submit(self, msg: dict[Any, Any]) -> None:
        document = Document(**msg['document'])
        overwrite = False
        if 'overwrite' in msg:
            overwrite = msg['overwrite']

        self.submit_document(document, overwrite=overwrite)

    def submit_document(self, document: Document, *, overwrite: bool = False) -> Document | None:
        if document.is_scanned is True and overwrite is False:
            return None

        self.host.update_mock_data_input(
            self,
            asdict(document),
        )

        async def send_message() -> Document:
            self.send_message_async(
                Service.Topic.DOCUMENT_CREATED,
                {'id': document.id, 'type': 'document', 'tracking_id': document.tracking_id},
            )
            return document

        future = self.run_task(send_message())
        future.add_done_callback(self.on_document_created_sent)
        return document

    def on_document_created_sent(self, ret: Future[Any]) -> None:
        document = ret.result()
        scan = Scan(self, document.repo_id, document.tracking_id)
        scan.parse_media_resource(document)
