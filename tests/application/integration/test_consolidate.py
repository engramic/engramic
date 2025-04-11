import logging
import sys

from engramic.application.consolidate.consolidate_service import ConsolidateService
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
        observation = self.host.mock_data_collector['CodifyService-output']
        self.send_message_async(Service.Topic.SET_TRAINING_MODE, {'training_mode': True})
        self.send_message_async(Service.Topic.OBSERVATION_COMPLETE, observation)


def test_response_service_submission() -> None:
    host = Host('mock', [MessageService, ConsolidateService, MiniService])

    def callback_test(generated_response) -> None:
        expected_results = host.mock_data_collector['ConsolidateService-output']

        assert str(generated_response) == str(expected_results)
        host.trigger_shutdown()

    consolidate_service = host.get_service(ConsolidateService)
    consolidate_service.subscribe(Service.Topic.INDEX_COMPLETE, callback_test)

    host.wait_for_shutdown(10)
