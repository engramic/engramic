import logging
import sys

import pytest

from engramic.application.message.message_service import MessageService
from engramic.application.retrieve.retrieve_service import RetrieveService
from engramic.core.host import Host
from engramic.infrastructure.system.service import Service

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.info('Using Python interpreter:%s', sys.executable)


class MiniService(Service):
    def start(self) -> None:
        super().start()
        self.subscribe(Service.Topic.RETRIEVE_COMPLETE, self.on_retrieve_complete)
        self.run_task(self.send_message())

    async def send_message(self) -> None:
        rs_input = self.host.mock_data_collector['RetrieveService-0-input']
        self.send_message_async(Service.Topic.SUBMIT_PROMPT, rs_input)

    def on_retrieve_complete(self, generated_results) -> None:
        expected_results = self.host.mock_data_collector['RetrieveService--0-output']

        assert str(generated_results['analysis']) == str(expected_results['analysis'])
        assert str(generated_results['prompt_str']) == str(expected_results['prompt_str'])

        # delete the ask ids since they are auto generated and won't match.
        del generated_results['retrieve_response']['ask_id']
        del expected_results['retrieve_response']['ask_id']
        del generated_results['retrieve_response']['input_id']
        del expected_results['retrieve_response']['input_id']

        assert str(generated_results['retrieve_response']) == str(expected_results['retrieve_response'])

        self.host.shutdown()


@pytest.mark.timeout(10)  # seconds
def test_retrieve_service_submission() -> None:
    host = Host('mock', [MessageService, RetrieveService, MiniService])

    host.wait_for_shutdown()
