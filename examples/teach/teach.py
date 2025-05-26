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
from engramic.application.teach.teach_service import TeachService
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
        self.subscribe(Service.Topic.LESSON_CREATED, self.on_lesson_created)
        self.subscribe(Service.Topic.LESSON_COMPLETED, self.on_lesson_completed)

        sense_service = self.host.get_service(SenseService)
        # document = Document(
        #    Document.Root.RESOURCE, 'engramic.resources.rag_document', 'IntroductiontoQuantumNetworking.pdf'
        # )
        document = Document(
            Document.Root.RESOURCE, 'engramic.resources.job_descriptions', 'GH SC Official Job Descriptions.pdf'
        )
        self.document_id = document.id
        sense_service.submit_document(document)

    def on_main_prompt_complete(self, message_in: dict[str, Any]) -> None:
        response = Response(**message_in)
        if not response.prompt['is_lesson']:
            logging.info('\n\n================[Response]==============\n%s\n\n', response.response)
        else:
            logging.info('Lesson Response. %s', response.prompt['prompt_str'])

    def on_lesson_created(self, message_in: dict[str, Any]) -> None:
        self.lesson_id = message_in['lesson_id']

    def on_lesson_completed(self, message_in: dict[str, Any]) -> None:
        lesson_id = message_in['lesson_id']
        if self.lesson_id == lesson_id:
            retrieve_service = self.host.get_service(RetrieveService)
            # retrieve_service.submit(Prompt('Please tell me about QuantumNetworking'))
            retrieve_service.submit(Prompt('Tell me about the company GH star collector.'))


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
            TeachService,
            ProgressService,
            TestService,
        ],
    )

    # The host continues to run and waits for a shutdown message to exit.
    host.wait_for_shutdown()


if __name__ == '__main__':
    main()
