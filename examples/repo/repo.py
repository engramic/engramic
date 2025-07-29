# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import logging
from typing import Any

from engramic.application.codify.codify_service import CodifyService
from engramic.application.consolidate.consolidate_service import ConsolidateService
from engramic.application.message.message_service import MessageService
from engramic.application.progress.progress_service import ProgressService
from engramic.application.repo.repo_service import RepoService
from engramic.application.response.response_service import ResponseService
from engramic.application.retrieve.retrieve_service import RetrieveService
from engramic.application.sense.sense_service import SenseService
from engramic.application.storage.storage_service import StorageService
from engramic.core.host import Host
from engramic.core.prompt import Prompt
from engramic.core.response import Response
from engramic.infrastructure.system import Service

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# This service is built only to subscribe to the main prompt completion message.
class TestService(Service):
    DOCUMENT_COUNT: int = 2

    def __init__(self, host):
        super().__init__(host)
        self.count = 0
        self.repos = {}

    def start(self):
        super().start()
        self.subscribe(Service.Topic.MAIN_PROMPT_COMPLETE, self.on_main_prompt_complete)
        self.subscribe(Service.Topic.REPO_DIRECTORY_SCANNED, self._on_repo_directory_scanned)
        self.subscribe(Service.Topic.REPO_UPDATE_REPOS, self._on_repo_update)
        self.subscribe(Service.Topic.DOCUMENT_INSERTED, self.on_document_inserted)
        repo_service = self.host.get_service(RepoService)
        repo_service.scan_folders()
        self.run_task(self.submit_documents())

    async def submit_documents(self) -> None:
        repo_service = self.host.get_service(RepoService)
        self.document_id1 = 'ebafc7af85629e1346863e4622087032'  # 'IntroductiontoQuantumNetworking.pdf'
        self.document_id2 = 'bb8f78c67efb2e7f5d843038ef5e072d'  # 'Elysian_Fields.pdf'
        repo_service.submit_ids([self.document_id1], overwrite=True)
        repo_service.submit_ids([self.document_id2])

    def _on_repo_directory_scanned(self, message_in: dict[str, Any]) -> None:
        if message_in['repos'] is not None:
            self.repos = message_in['repos']
            self.repo_id1 = next(
                (key for key, value in self.repos.items() if value['name'] == 'QuantumNetworking'), None
            )
            self.repo_id2 = next((key for key, value in self.repos.items() if value['name'] == 'ElysianFields'), None)
        else:
            logging.info('No repos found. You can add a repo by adding a folder to home/.local/share/engramic')

    def _on_repo_update(self, message_in: dict[str, Any]) -> None:
        # Only logging information about the files
        logging.info('Repo: %s, Files received: %d', message_in['repo'], len(message_in['files']))
        for file in message_in['files']:
            status = 'previously scanned' if file['percent_complete_document'] > 1 else 'unscanned'
            logging.info('File: %s - %s', file['file_name'], status)

    def on_document_inserted(self, message_in: dict[str, Any]) -> None:
        document_id = message_in['id']
        if document_id in {self.document_id1, self.document_id2}:
            self.count += 1
            if self.count == TestService.DOCUMENT_COUNT:
                retrieve_service = self.host.get_service(RetrieveService)
                prompt1 = Prompt(
                    'This is prompt 1. Briefly tell me about IntroductiontoQuantumNetworking.pdf and Elysian_Fields.pdf. Start with prompt number.',
                    repo_ids_filters=[self.repo_id1, self.repo_id2],
                )
                retrieve_service.submit(prompt1)
                prompt2 = Prompt(
                    'This is prompt 2. Briefly tell me about IntroductiontoQuantumNetworking.pdf and Elysian_Fields.pdf. Start with prompt number.',
                    repo_ids_filters=[self.repo_id1],
                )
                retrieve_service.submit(prompt2)
                prompt3 = Prompt(
                    'This is prompt 3. Briefly tell me about IntroductiontoQuantumNetworking.pdf and Elysian_Fields.pdf.  Start with prompt number.',
                    repo_ids_filters=None,
                )  # means that repos are not being used. All files not loaded as part of a repo are in a default repo known as the 'null' repo.
                retrieve_service.submit(prompt3)

                # The following would throw an exception. Null set is an invalid input.
                # prompt4 = Prompt('This is prompt 4. Tell me about IntroductiontoQuantumNetworking.pdf and Elysian_Fields.pdf',repo_ids_filters=[])
                # retrieve_service.submit(prompt4)

    def on_main_prompt_complete(self, message_in: dict[str, Any]) -> None:
        response = Response(**message_in)
        if not response.prompt['is_lesson']:
            logging.info('\n\n================[Response]==============\n%s\n\n', response.response)
        else:
            logging.info('Lesson Response. %s', response.prompt['prompt_str'])


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
            RepoService,
            ProgressService,
            TestService,
        ],
    )

    # The host continues to run and waits for a shutdown message to exit.
    host.wait_for_shutdown()


if __name__ == '__main__':
    main()
