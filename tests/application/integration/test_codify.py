import logging
import sys

from engramic.application.codify.codify_service import CodifyService
from engramic.application.message.message_service import MessageService
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
        main_propmpt_response = self.host.mock_data_collector['ResponseService-output']
        self.send_message_async(Service.Topic.SET_TRAINING_MODE, {'training_mode': True})
        self.send_message_async(Service.Topic.MAIN_PROMPT_COMPLETE, main_propmpt_response)


def test_response_service_submission() -> None:
    host = Host('mock', [MessageService, CodifyService, MiniService])

    def callback_test(generated_response) -> None:
        expected_results = host.mock_data_collector['CodifyService-output']

        for d in [generated_response, expected_results]:
            d.pop('id', None)
            d.get('meta', {}).pop('id', None)

        # Remove 'id' from each engram in the engram_list
        for gen_engram, exp_engram in zip(
            generated_response.get('engram_list', []), expected_results.get('engram_list', [])
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

        host.trigger_shutdown()

    codify_service = host.get_service(CodifyService)
    codify_service.subscribe(Service.Topic.OBSERVATION_COMPLETE, callback_test)

    host.wait_for_shutdown(10)
