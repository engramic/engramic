
import logging
import sys
from dataclasses import asdict
from typing import Any

import pytest

from engramic.application.message.message_service import MessageService
from engramic.application.progress.progress_service import ProgressService
from engramic.application.repo.repo_service import RepoService
from engramic.application.response.response_service import ResponseService
from engramic.application.retrieve.retrieve_service import RetrieveService
from engramic.application.sense.sense_service import SenseService
from engramic.core.host import Host
from engramic.core.prompt import Prompt
from engramic.core.response import Response
from engramic.infrastructure.system.service import Service

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.info('Using Python interpreter:%s', sys.executable)

class TestService(Service):
    def __init__(self, host):
        self.repo_id1 = None
        super().__init__(host)

    def start(self) -> None:
        self.subscribe(Service.Topic.REPO_DIRECTORY_SCANNED, self._on_repo_directory_scanned)
        self.subscribe(Service.Topic.MAIN_PROMPT_COMPLETE, self.on_main_prompt_complete)
        super().start()

    def _on_repo_directory_scanned(self, message_in: dict[str, Any]) -> None:
        if message_in['repos'] is not None:
            self.repos = message_in['repos']
            self.repo_id1 = next(
                (key for key, value in self.repos.items() if value['name'] == 'Backbranch'), None
            )
        else:
            logging.info('No repos found. You can add a repo by adding a folder to home/.local/share/engramic')

        async def SendMessage() -> None:
            _prompt = Prompt("Validate the math is correct for the tables in BoardPresentation.pdf.", repo_ids_filters=[self.repo_id1], include_default_repos=False, thinking_level=0.2)
            self.send_message_async(Service.Topic.SUBMIT_PROMPT, asdict(_prompt))


        self.run_task(SendMessage())

    def on_main_prompt_complete(self, message_in: dict[str, Any]) -> None:
        response = Response(**message_in)
        logging.info('\n\n================[Response]==============\n%s\n\n', response.response)


@pytest.mark.timeout(100)  # seconds
def test_doc_process() -> None:
    host = Host(
        'standard',
        [
            MessageService,
            SenseService,
            RetrieveService,
            ResponseService,
            RepoService,
            ProgressService,
            TestService,
        ],
    )


    host.wait_for_shutdown()
