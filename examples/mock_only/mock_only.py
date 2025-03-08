# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import logging

from engramic.application.retrieve import Ask, RetrieveService
from engramic.core import Library, Prompt
from engramic.infrastructure.system import Host

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def main() -> None:
    retrieve_service = RetrieveService()
    host = Host([retrieve_service],"mock")

    ask = Ask(Prompt('What is your name?'))
    retrieve_service.submit(ask)

    host.wait_for_shutdown()


if __name__ == '__main__':
    main()
