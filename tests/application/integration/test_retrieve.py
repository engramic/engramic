import logging
import sys

from engramic.application.message.message_service import MessageService
from engramic.application.retrieve.retrieve_service import RetrieveService
from engramic.core import Prompt
from engramic.infrastructure.system import Host

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.info('Using Python interpreter:%s', sys.executable)


def test_retrieve_service_submission() -> None:
    host = Host('mock', [MessageService, RetrieveService])

    """Integration test to check if RetrieveService submits prompts correctly."""
    prompt = Prompt('Give me a recipe for queso, put the ingredients in a table.')

    def callback_test(data: list[int]) -> None:
        assert data == [9, 20, 4]

    retrieve_service = host.get_service(RetrieveService)
    retrieve_service.subscribe(RetrieveService.Topic.RETRIEVE_COMPLETE, callback_test)

    retrieve_service.submit(prompt)
