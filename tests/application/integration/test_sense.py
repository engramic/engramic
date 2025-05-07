import logging
import sys
from typing import Any

import pytest

from engramic.application.message.message_service import MessageService
from engramic.application.sense.sense_service import SenseService
from engramic.core.host import Host
from engramic.infrastructure.system.service import Service

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.info('Using Python interpreter:%s', sys.executable)


class MiniService(Service):
    def start(self) -> None:
        super().start()
        self.subscribe(Service.Topic.OBSERVATION_COMPLETE, self.on_observation_completed)
        self.run_task(self.send_message())

    async def send_message(self) -> None:
        sense_service_input = self.host.mock_data_collector['SenseService-0-input']
        self.send_message_async(Service.Topic.SUBMIT_DOCUMENT, sense_service_input)

    def on_observation_completed(self, generated_observation: dict[Any, Any]) -> None:
        expected_results = self.host.mock_data_collector['SenseService--0-output']

        expected_meta = expected_results['meta']
        generated_meta = generated_observation['meta']

        del expected_meta['id']
        del generated_meta['id']

        assert expected_meta == generated_meta

        expected_engrams = expected_results['engram_list']
        for engram in expected_engrams:
            del engram['id']
            del engram['created_date']
            del engram['meta_ids']

        generated_engrams = generated_observation['engram_list']
        for engram in generated_engrams:
            del engram['id']
            del engram['created_date']
            del engram['meta_ids']

        assert expected_engrams == generated_engrams

        self.host.shutdown()


@pytest.mark.timeout(10)  # seconds
def test_sense_service_submission() -> None:
    host = Host('mock', [MessageService, SenseService, MiniService])
    host.wait_for_shutdown()
