# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import uuid
from typing import Any

from engramic.application.sense.scan import Scan
from engramic.core.document import Document
from engramic.core.host import Host
from engramic.infrastructure.system.service import Service


class SenseService(Service):
    """
    Sense currently support documents as it's only input system. Other formats that are not document based will be available in the future.

    This service listens for document submission events, initializes a scan process that parses the media
    resource, and notifies the system of newly created inputs.

    Attributes:
        sense_initial_summary (Plugin): Plugin for generating an inital summary of the document.
        sense_scan_page (Plugin): Plugin for scanning and interpreting document content.
        sense_full_summary (Plugin): Plugin for producing full document summaries.

    Methods:
        init_async(): Initializes the service asynchronously and sets up any required connections or state.
        start(): Subscribes to the system topic for document submissions.
        on_document_submit(msg: dict): Extracts file information from a message and submits the document.
        submit_document(document: Document): Triggers scanning of the submitted document and sends async notification.
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
        file_path = msg['file_path']
        file_name = msg['file_name']
        path_type = msg['root_directory']
        self.submit_document(Document(Document.Root(path_type), file_path, file_name))

    def submit_document(self, document: Document) -> None:
        if __debug__:
            self.host.update_mock_data_input(
                self,
                {
                    'file_path': document.file_path,
                    'file_name': document.file_name,
                    'root_directory': document.root_directory.value,
                },
            )

        scan = Scan(self, str(uuid.uuid4()))
        scan.parse_media_resource(document)

        async def send_message() -> None:
            self.send_message_async(Service.Topic.INPUT_CREATED, {'input_id': document.id})

        self.run_task(send_message())
