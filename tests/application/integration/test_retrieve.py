import logging
import sys

import pytest
from engramic.application.message.message_service import MessageService
from engramic.application.retrieve.retrieve_service import RetrieveService
from engramic.core import Prompt
from engramic.infrastructure.system import Host

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.info('Using Python interpreter:%s', sys.executable)


@pytest.fixture
def host():
    """Fixture to set up and tear down the host."""
    test_host = Host('mock', [MessageService, RetrieveService])
    yield test_host  # Provide the fixture to the test
    test_host.shutdown()  # Ensure proper cleanup


@pytest.fixture
def retrieve_service(host):
    """Fixture to get the RetrieveService instance."""
    return host.get_service(RetrieveService)


def test_retrieve_service_submission(retrieve_service):
    """Integration test to check if RetrieveService submits prompts correctly."""
    prompt = Prompt('Give me a recipe for queso, put the ingredients in a table.')

    def callback_test(data):
        assert data == [9, 20, 4]

    retrieve_service.subscribe(RetrieveService.Topic.RETRIEVE_COMPLETE, callback_test)

    retrieve_service.submit(prompt)
