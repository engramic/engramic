import json
import logging
import sys

from engramic.application.codify.codify_service import CodifyService
from engramic.application.consolidate.consolidate_service import ConsolidateService
from engramic.application.message.message_service import MessageService
from engramic.application.response.response_service import ResponseService
from engramic.application.retrieve.retrieve_service import RetrieveService
from engramic.application.storage.storage_service import StorageService
from engramic.core.host import Host
from engramic.core.prompt import Prompt

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.info('Using Python interpreter:%s', sys.executable)


def test_retrieve_service_submission() -> None:
    host = Host(
        'mock', [MessageService, RetrieveService, ResponseService, StorageService, CodifyService, ConsolidateService]
    )

    prompt = Prompt('Tell me about the All In podcast.')

    def callback_test(data) -> None:
        indices_mock = json.loads(host.mock_data_collector['_generate_indices-retrieve_gen_index-0']['llm_response'])
        indices_response = data['analysis']['indices']
        assert indices_mock == indices_response

        retrieve_mock: list[str] = list(host.mock_data_collector['_query_index_db-db-0']['query_set'])
        retreive_response = data['retrieve_response']['engram_id_array']
        assert retrieve_mock == retreive_response
        host.trigger_shutdown()

    retrieve_service = host.get_service(RetrieveService)
    retrieve_service.subscribe(RetrieveService.Topic.RETRIEVE_COMPLETE, callback_test)
    retrieve_service.submit(prompt)

    host.wait_for_shutdown(10)
