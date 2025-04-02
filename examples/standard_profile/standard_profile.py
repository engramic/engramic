# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import logging
import sys

from engramic.application.codify.codify_service import CodifyService
from engramic.application.consolidate.consolidate_service import ConsolidateService
from engramic.application.message.message_service import MessageService
from engramic.application.response.response_service import ResponseService
from engramic.application.retrieve.retrieve_service import RetrieveService
from engramic.application.storage.storage_service import StorageService
from engramic.core.host import Host
from engramic.core.prompt import Prompt

# Configure logging
# logging.basicConfig(filename='output.log',level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.info('Using Python interpreter:%s', sys.executable)


def main() -> None:
    host = Host(
        'standard',
        [MessageService, RetrieveService, ResponseService, StorageService, CodifyService, ConsolidateService]
    )

    retrieve_service = host.get_service(RetrieveService)
    retrieve_service.submit(Prompt('Briefly tell me about the All In podcast.'))
    # time.sleep(10)
    # retrieve_service.submit(Prompt('Briefly tell me about Chamath Palihapitiya.'))

    # The host continues to run and waits for a shutdown message to exit.
    host.wait_for_shutdown()


if __name__ == '__main__':
    main()
