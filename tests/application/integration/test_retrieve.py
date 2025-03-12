import pytest
import logging
import sys
from engramic.application.retrieve.retrieve_service import RetrieveService
from engramic.application.message.message_service import MessageService
from engramic.core import Prompt
from engramic.infrastructure.system import Host

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.info('Using Python interpreter:%s', sys.executable)

@pytest.fixture
def host():
    """Fixture to set up and tear down the host."""
    Host.register_service(MessageService)
    Host.register_service(RetrieveService)
    test_host = Host('mock')
    yield test_host  # Provide the fixture to the test
    test_host.shutdown()  # Ensure proper cleanup

@pytest.fixture
def retrieve_service(host):
    """Fixture to get the RetrieveService instance."""
    return host.get_service(RetrieveService)

def test_retrieve_service_submission(retrieve_service):
    """Integration test to check if RetrieveService submits prompts correctly."""
    prompt = Prompt('Give me a recipe for queso, put the ingredients in a table.')
    fut = retrieve_service.submit(prompt)
    result = fut.result(timeout=5)
    # You might need a way to verify the response, such as checking logs, mock calls, or output.
    # This part depends on how RetrieveService handles submissions.
    assert result==[9,20,4]  # Placeholder assertion; replace with a meaningful verification