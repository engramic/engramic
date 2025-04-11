import logging
import sys

from engramic.application.message.message_service import MessageService
from engramic.application.response.response_service import ResponseService
from engramic.core.host import Host
from engramic.infrastructure.system.service import Service

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.info('Using Python interpreter:%s', sys.executable)


class MiniService(Service):
    def start(self):
        return super().start()

    def init_async(self):
        super().init_async()
        retrieve_response = self.host.mock_data_collector['RetrieveService-output']

        self.send_message_async(Service.Topic.RETRIEVE_COMPLETE, retrieve_response)


def test_response_service_submission() -> None:
    host = Host('mock', [MessageService, ResponseService, MiniService])

    def callback_test(generated_response) -> None:
        expected_results = host.mock_data_collector['ResponseService-output']
        del generated_response['id']
        del expected_results['id']
        del generated_response['response_time']
        del expected_results['response_time']
        del generated_response['model']
        del expected_results['model']
        assert str(generated_response) == str(expected_results)
        host.trigger_shutdown()

    response_service = host.get_service(ResponseService)
    response_service.subscribe(Service.Topic.MAIN_PROMPT_COMPLETE, callback_test)

    host.wait_for_shutdown(10)
