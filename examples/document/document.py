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
from engramic.core.response import Response
from engramic.infrastructure.system import Service

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# This service is built only to subscribe to the main prompt completion message.
class TestService(Service):
    def start(self):
        super().start()
        self.subscribe(Service.Topic.MAIN_PROMPT_COMPLETE, self.on_main_prompt_complete)
        self.subscribe(Service.Topic.INPUT_COMPLETED, self.on_input_complete)

        sense_service = self.host.get_service(SenseService)
        document = Document(
            Document.Root.RESOURCE, 'engramic.resources.job_descriptions', 'GH SC Official Job Descriptions.pdf'
        )
        # document = Document(
        #    Document.Root.RESOURCE, 'engramic.resources.rag_document', 'IntroductiontoQuantumNetworking.pdf'
        # )
        self.document_id = document.id
        sense_service.submit_document(document)

    def on_main_prompt_complete(self, message_in: dict[str, Any]) -> None:
        response = Response(**message_in)
        logging.info('\n\n================[Response]==============\n%s\n\n', response.response)

    def on_input_complete(self, message_in: dict[str, Any]) -> None:
        source_id = message_in['source_id']
        if self.document_id == source_id:
            retrieve_service = self.host.get_service(RetrieveService)
            # prompt = Prompt('Please tell me about IntroductiontoQuantumNetworking.pdf')
            prompt = Prompt('Tell me about the company in GH SC Official Job Descriptions.pdf.')
            retrieve_service.submit(prompt)


def main() -> None:
    host = Host(
        'standard',
        [
            MessageService,
            SenseService,
            RetrieveService,
            ResponseService,
            StorageService,
            ConsolidateService,
            CodifyService,
            ProgressService,
            TestService,
        ],
    )

    # The host continues to run and waits for a shutdown message to exit.
    host.wait_for_shutdown()


if __name__ == '__main__':
    main()
