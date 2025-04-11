import logging
import sys

from engramic.application.message.message_service import MessageService
from engramic.application.retrieve.retrieve_service import RetrieveService
from engramic.core.host import Host
from engramic.core.prompt import Prompt

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.info('Using Python interpreter:%s', sys.executable)


def test_retrieve_service_submission() -> None:
    host = Host('mock', [MessageService, RetrieveService])

    prompt = Prompt(**host.mock_data_collector['RetrieveService-input'])

    def callback_test(generated_results) -> None:
        expected_results = host.mock_data_collector['RetrieveService-output']

        assert str(generated_results['analysis']) == str(expected_results['analysis'])
        assert str(generated_results['prompt_str']) == str(expected_results['prompt_str'])

        # delete the ask ids since they are auto generated and won't match.
        del generated_results['retrieve_response']['ask_id']
        del expected_results['retrieve_response']['ask_id']

        assert str(generated_results['retrieve_response']) == str(expected_results['retrieve_response'])

        host.trigger_shutdown()

    retrieve_service = host.get_service(RetrieveService)
    retrieve_service.subscribe(RetrieveService.Topic.RETRIEVE_COMPLETE, callback_test)
    retrieve_service.submit(prompt)

    host.wait_for_shutdown(10)
