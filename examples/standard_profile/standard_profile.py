# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import logging
from typing import Any

from engramic.application.codify.codify_service import CodifyService
from engramic.application.consolidate.consolidate_service import ConsolidateService
from engramic.application.message.message_service import MessageService
from engramic.application.response.response_service import ResponseService
from engramic.application.retrieve.retrieve_service import RetrieveService
from engramic.application.storage.storage_service import StorageService
from engramic.core.host import Host
from engramic.core.prompt import Prompt
from engramic.core.response import Response
from engramic.infrastructure.system import Service

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# This service is built only to subscribe to the main prompt completion message.
class TestService(Service):
    def start(self):
        self.subscribe(Service.Topic.MAIN_PROMPT_COMPLETE, self.on_main_prompt_complete)
        return super().start()

    def on_main_prompt_complete(self, message_in: dict[str, Any]) -> None:
        response = Response(**message_in)
        logging.info('\n\n================[Response]==============\n%s\n\n', response.response)


def main() -> None:
    host = Host(
        'standard',
        [
            MessageService,
            TestService,
            RetrieveService,
            ResponseService,
            CodifyService,  # not used in this example
            ConsolidateService,  # not used in this example
            StorageService,  # not used in this example
        ],
    )

    retrieve_service = host.get_service(RetrieveService)
    retrieve_service.submit(Prompt('Briefly tell me about Chamath Palihapitiya.'))

    # The host continues to run and waits for a shutdown message to exit.
    host.wait_for_shutdown()


if __name__ == '__main__':
    main()
