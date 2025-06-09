# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import logging
import sys

import pytest

from engramic.application.message.message_service import MessageService
from engramic.application.response.response_service import ResponseService
from engramic.core.host import Host
from engramic.infrastructure.system.service import Service

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.info('Using Python interpreter:%s', sys.executable)


class MiniService(Service):
    def start(self) -> None:
        super().start()
        self.run_task(self.send_message())
        self.subscribe(Service.Topic.MAIN_PROMPT_COMPLETE, self.on_response_complete)

    async def send_message(self) -> None:
        retrieve_response = self.host.mock_data_collector['RetrieveService--output']
        self.send_message_async(Service.Topic.RETRIEVE_COMPLETE, retrieve_response)

    def on_response_complete(self, generated_response) -> None:
        expected_results = self.host.mock_data_collector['ResponseService--output']
        del generated_response['id']
        del expected_results['id']
        del generated_response['response_time']
        del expected_results['response_time']
        del generated_response['model']
        del expected_results['model']
        del generated_response['source_id']
        del expected_results['source_id']
        generated_response = str(generated_response)
        expected_results = str(expected_results)
        assert generated_response == expected_results
        self.host.shutdown()


@pytest.mark.timeout(10)  # seconds
def test_response_service_submission() -> None:
    host = Host('mock', [MessageService, ResponseService, MiniService])

    host.wait_for_shutdown()
