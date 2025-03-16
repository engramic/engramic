# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import logging
import sys
import time

from engramic.application.message.message_service import MessageService
from engramic.application.retrieve.retrieve_service import RetrieveService
from engramic.application.response.response_service import ResponseService
from engramic.core import Prompt
from engramic.infrastructure.system import Host

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.info('Using Python interpreter:%s', sys.executable)

def test_submit():
    print("Function executed after 10 seconds")

def main() -> None:
    host = Host('mock', [MessageService, RetrieveService,ResponseService])

    retrieve_service = host.get_service(RetrieveService)

    def callback_test(data):
        logging.info('Callback result: %s', data)

    retrieve_service.subscribe(RetrieveService.Topic.RETRIEVE_COMPLETE, callback_test)

    time.sleep(10)

    # Submit the prompt.
    retrieve_service.submit(Prompt('Give me a recepie for queso, put the ingredients in a table.'))

    # The host continues to run and waits for a shutdown message to exit.
    host.wait_for_shutdown()


if __name__ == '__main__':
    main()
