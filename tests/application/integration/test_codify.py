import logging
import sys

import pytest

from engramic.application.codify.codify_service import CodifyService
from engramic.application.message.message_service import MessageService
from engramic.core.host import Host
from engramic.infrastructure.system.service import Service

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.info('Using Python interpreter:%s', sys.executable)


class MiniService(Service):
    def start(self) -> None:
        self.subscribe(Service.Topic.OBSERVATION_COMPLETE, self.on_observation_complete)
        self.run_task(self.send_messages())
        super().start()

    async def send_messages(self) -> None:
        main_propmpt_response = self.host.mock_data_collector['ResponseService-0-output']
        self.send_message_async(Service.Topic.SET_TRAINING_MODE, {'training_mode': True})
        self.send_message_async(Service.Topic.MAIN_PROMPT_COMPLETE, main_propmpt_response)

    def on_observation_complete(self, generated_response) -> None:
        expected_results = self.host.mock_data_collector['CodifyService-0-output']

        for d in [generated_response, expected_results]:
            d.pop('id', None)
            d.get('meta', {}).pop('id', None)

        # Remove 'id' from each engram in the engram_list
        for gen_engram, exp_engram in zip(
            generated_response.get('engram_list', []), expected_results.get('engram_list', []), strict=False
        ):
            gen_engram.pop('id', None)
            exp_engram.pop('id', None)
            gen_engram.pop('created_date', None)
            exp_engram.pop('created_date', None)
            gen_engram.pop('meta_ids', None)
            exp_engram.pop('meta_ids', None)

        assert len(generated_response['engram_list']) == len(expected_results['engram_list'])
        assert str(generated_response['meta']) == str(expected_results['meta'])
        assert str(generated_response['engram_list']) == str(expected_results['engram_list'])

        self.host.shutdown()


@pytest.mark.timeout(10)  # seconds
def test_codify_service_submission() -> None:
    host = Host('mock', [MessageService, CodifyService, MiniService])

    host.wait_for_shutdown()
