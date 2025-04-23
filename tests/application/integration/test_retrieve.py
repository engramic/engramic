import logging
import sys

import pytest

from engramic.application.message.message_service import MessageService
from engramic.application.retrieve.retrieve_service import RetrieveService
from engramic.core.host import Host
from engramic.core.prompt import Prompt
from engramic.infrastructure.system.service import Service

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.info('Using Python interpreter:%s', sys.executable)


class MiniService(Service):
    def start(self) -> None:
        self.subscribe(Service.Topic.RETRIEVE_COMPLETE, self.on_retrieve_complete)
        self.run_task(self.send_message())
        super().start()

    async def send_message(self) -> None:
        prompt = Prompt(**self.host.mock_data_collector['RetrieveService-input'])
        self.send_message_async(Service.Topic.SUBMIT_PROMPT, prompt.prompt_str)

    def on_retrieve_complete(self, generated_results) -> None:
        expected_results = self.host.mock_data_collector['RetrieveService-0-output']

        assert str(generated_results['analysis']) == str(expected_results['analysis'])
        assert str(generated_results['prompt_str']) == str(expected_results['prompt_str'])

        # delete the ask ids since they are auto generated and won't match.
        del generated_results['retrieve_response']['ask_id']
        del expected_results['retrieve_response']['ask_id']

        assert str(generated_results['retrieve_response']) == str(expected_results['retrieve_response'])

        self.host.shutdown()


@pytest.mark.timeout(10)  # seconds
def test_retrieve_service_submission() -> None:
    host = Host('mock', [MessageService, RetrieveService, MiniService])
    host.shutdown()
    host.wait_for_shutdown()
