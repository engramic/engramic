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
    def __init__(self, host: Host) -> None:
        super().__init__(host)
        self.sense_inital_summary = host.plugin_manager.get_plugin('llm', 'sense_initial_summary')
        self.sense_scan_page = host.plugin_manager.get_plugin('llm', 'sense_scan')
        self.sense_full_summary = host.plugin_manager.get_plugin('llm', 'sense_full_summary')

    def init_async(self) -> None:
        return super().init_async()

    def start(self) -> None:
        self.subscribe(Service.Topic.SUBMIT_DOCUMENT, self.on_document_submit)
        super().start()

    def on_document_submit(self, msg: dict[Any, Any]) -> None:
        resource_path = msg['resource_path']
        file_name = msg['file_name']
        self.submit_document(Document(True, resource_path, file_name))

    def submit_document(self, document: Document) -> None:
        if __debug__:
            self.host.update_mock_data_input(
                self,
                {
                    'resource_path': document.resource_path,
                    'file_name': document.file_name,
                    'is_resource': document.is_resource,
                },
            )

        if document.is_resource:
            scan = Scan(self, str(uuid.uuid4()))
            scan.parse_media_resource(document)

        else:
            error = 'Only resource documents are currently supported.'
            raise NotImplementedError(error)

        self.send_message_async(Service.Topic.INPUT_CREATED, {'input_id': document.get_source_id()})
