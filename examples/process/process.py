# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import logging
from typing import Any

from engramic.application.codify.codify_service import CodifyService
from engramic.application.consolidate.consolidate_service import ConsolidateService
from engramic.application.message.message_service import MessageService
from engramic.application.process.process import Process
from engramic.application.process.process_service import ProcessService
from engramic.application.progress.progress_service import ProgressService
from engramic.application.repo.repo_service import RepoService
from engramic.application.response.response_service import ResponseService
from engramic.application.retrieve.retrieve_service import RetrieveService
from engramic.application.sense.sense_service import SenseService
from engramic.application.storage.storage_service import StorageService
from engramic.core.host import Host
from engramic.core.response import Response
from engramic.infrastructure.system import Service

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class TestService(Service):
    def start(self):
        super().start()
        self.subscribe(Service.Topic.MAIN_PROMPT_COMPLETE, self.on_main_prompt_complete)
        self.subscribe(Service.Topic.PROCESS_ACTIVE_PROGRESS_UPDATED, self.on_active_process_updated)
        self.subscribe(Service.Topic.PROCESS_RECENT_PROGRESS_UPDATED, self.on_recent_process_updated)
        self.run_task(self.create_process('Hi, how are you doing?'))

    async def create_process(self, input_prompt: str) -> None:
        self.send_message_async(
            Service.Topic.PROCESS_CREATE,
            {
                'process_type': Process.ProcessType.PROMPT_ONLY.value,
                'input_prompt': input_prompt,
                'selected_repos': None,
            },
        )

    def on_main_prompt_complete(self, message_in: dict[str, Any]) -> None:
        response = Response(**message_in)
        logging.info('\n\n================[Response]==============\n%s\n\n', response.response)

    def on_active_process_updated(self, message_in: dict[str, Any]) -> None:
        logging.info('\n\n================[Active Process]==============\n\n')
        process = Process(**message_in)
        logging.info(process)

    def on_recent_process_updated(self, message_in: dict[str, Any]) -> None:
        logging.info('\n\n================[Recent Process]==============\n\n')
        for process_dict in message_in['recent_progress_list']:
            process = Process(**process_dict)
            logging.info(process)


def main() -> None:
    host = Host(
        'standard',
        [
            MessageService,
            RetrieveService,
            ResponseService,
            CodifyService,
            ConsolidateService,
            StorageService,
            ProcessService,
            ProgressService,
            SenseService,
            RepoService,
            TestService,
        ],
    )

    # The host continues to run and waits for a shutdown message to exit.
    host.wait_for_shutdown()


if __name__ == '__main__':
    main()
