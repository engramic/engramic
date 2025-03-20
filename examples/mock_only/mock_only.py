# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import logging
import sys

from engramic.application.codify.codify_service import CodifyService
from engramic.application.message.message_service import MessageService
from engramic.application.response.response_service import ResponseService
from engramic.application.retrieve.retrieve_service import RetrieveService
from engramic.application.storage.storage_service import StorageService
from engramic.core.prompt import Prompt
from engramic.infrastructure.system import Host

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.info('Using Python interpreter:%s', sys.executable)


def main() -> None:
    host = Host('mock', [MessageService, RetrieveService, ResponseService, StorageService, CodifyService])

    retrieve_service = host.get_service(RetrieveService)
    retrieve_service.submit(Prompt('Give me a recepie for queso, put the ingredients in a table.'))

    # The host continues to run and waits for a shutdown message to exit.
    host.wait_for_shutdown()


if __name__ == '__main__':
    main()
