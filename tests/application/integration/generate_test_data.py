# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import logging
from typing import Any

from engramic.application.codify.codify_service import CodifyService
from engramic.application.consolidate.consolidate_service import ConsolidateService
from engramic.application.message.message_service import MessageService
from engramic.application.progress.progress_service import ProgressService
from engramic.application.response.response_service import ResponseService
from engramic.application.retrieve.retrieve_service import RetrieveService
from engramic.application.sense.sense_service import SenseService
from engramic.application.storage.storage_service import StorageService
from engramic.core.document import Document
from engramic.core.host import Host
from engramic.core.prompt import Prompt
from engramic.infrastructure.system import Service

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# This service is built only to subscribe to the main prompt completion message.
class TestService(Service):
    def start(self):
        super().start()
        self.subscribe(Service.Topic.PROMPT_INSERTED, self.on_prompt_inserted)
        self.subscribe(Service.Topic.DOCUMENT_INSERTED, self.on_document_inserted)
        self.run_task(self.start_test())

    def init_async(self):
        super().init_async()

    async def start_test(self) -> None:
        retrive_service = self.host.get_service(RetrieveService)
        prompt = Prompt(
            'What is the most notable applications of quantum networking? Why is maintaining quantum engablement over long distances notoriously difficult?',
            training_mode=True,
            tracking_id=1,
        )
        self.prompt_id = prompt.prompt_id
        retrive_service.submit(prompt)

    def on_prompt_inserted(self, message_in: dict[str, Any]) -> None:
        prompt_id = message_in['id']

        if prompt_id == self.prompt_id:
            sense_service = self.host.get_service(SenseService)
            document = Document(
                Document.Root.RESOURCE.value, 'engramic.resources.rag_document', 'IntroductiontoQuantumNetworking.pdf'
            )
            self.document_id = document.id
            document.tracking_id = 2
            sense_service.submit_document(document)

    def on_document_inserted(self, message_in: dict[str, Any]) -> None:
        document_id = message_in['id']

        if document_id == self.document_id:
            self.host.write_mock_data()


def main() -> None:
    host = Host(
        'standard',
        [
            MessageService,
            SenseService,
            RetrieveService,
            ResponseService,
            StorageService,
            CodifyService,
            ConsolidateService,
            ProgressService,
            TestService,
        ],
        generate_mock_data=True,
    )

    # The host continues to run and waits for a shutdown message to exit.
    host.wait_for_shutdown()


if __name__ == '__main__':
    main()
