# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import uuid

from engramic.application.sense.document import Document
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
        super().start()

    def document_submit_resource(self, resource_path: str, file_name: str) -> None:
        document = Document(self, str(uuid.uuid4()), self.sense_inital_summary)
        document.parse_media_resource(resource_path, file_name)
