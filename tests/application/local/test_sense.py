# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import logging
import sys
from dataclasses import asdict
from typing import Any

import pytest

from engramic.application.message.message_service import MessageService
from engramic.application.sense.sense_service import SenseService
from engramic.core.file_node import FileNode
from engramic.core.host import Host
from engramic.infrastructure.system.service import Service

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.info('Using Python interpreter:%s', sys.executable)

logging.getLogger('uvicorn.error').setLevel(logging.DEBUG)
logging.getLogger('uvicorn.access').setLevel(logging.DEBUG)
logging.getLogger('fastapi').setLevel(logging.DEBUG)


class MiniService(Service):
    def start(self) -> None:
        super().start()
        self.run_task(self.send_message())
        self.subscribe(Service.Topic.OBSERVATION_COMPLETE, self.on_observation_completed)

    async def send_message(self) -> None:
        document = FileNode(
            FileNode.Root.RESOURCE.value,
            'IntroductiontoQuantumNetworking.pdf',
            module_path='engramic.resources.rag_document',
        )
        self.document_id = document.id
        self.send_message_async(Service.Topic.DOCUMENT_SCAN_DOCUMENT, {'document': asdict(document)})

    def on_observation_completed(self, message: dict[str, Any]) -> None:
        del message
        self.host.shutdown()


@pytest.mark.timeout(timeout=10)  # seconds
def test_sense_service_submission() -> None:
    host = Host('mock', [MessageService, SenseService, MiniService], http_ports=[None, 9111, None])
    host.wait_for_shutdown()
