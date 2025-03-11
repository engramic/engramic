from concurrent.futures import Future
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Import your class under test
from engramic.application.retrieve.ask import Ask

# Import the interfaces that you plan to mock
from engramic.core import Prompt
from engramic.infrastructure.system.plugin_manager import PluginManager
from engramic.infrastructure.system.service import Service


@pytest.fixture
def mock_prompt():
    return MagicMock(spec=Prompt)


@pytest.fixture
def mock_plugin_manager():
    plugin_manager = MagicMock(spec=PluginManager)

    # Mock async plugins
    plugin_manager.get_plugin.side_effect = [
        {'func': AsyncMock(), 'args': {}},  # retrieve_gen_conversation_direction
        {'func': AsyncMock(), 'args': {}},  # retrieve_prompt_analysis
        {'func': AsyncMock(), 'args': {}},  # retrieve_gen_index
        {'func': AsyncMock(), 'args': {}},  # query_index_db
    ]

    return plugin_manager


@pytest.fixture
def mock_service():
    service = MagicMock(spec=Service)

    # Create Future objects to simulate async tasks
    future_direction = Future()
    future_direction.set_result({
        '_retrieve_gen_conversation_direction': {'conversation_direction': 'this is the conversation direction'}
    })

    future_analyze = Future()
    future_analyze.set_result({'prompt_analysis': 'analysis_done'})

    future_query = Future()
    future_query.set_result({'_query_index_db': 'some_result'})

    # Store futures separately for assertions
    service.futures = [future_direction, future_analyze, future_query]

    # Simulate the sequence of service.submit_async_tasks calls
    service.submit_async_tasks.side_effect = service.futures

    return service


@pytest.mark.asyncio
async def test_get_sources(mock_prompt, mock_plugin_manager, mock_service):
    ask = Ask(prompt=mock_prompt, plugin_manager=mock_plugin_manager)

    with (
        patch.object(Ask, '_retrieve_gen_conversation_direction', new_callable=AsyncMock) as mock_direction,
        patch.object(Ask, '_analyze_prompt', new_callable=AsyncMock) as mock_analyze,
        patch.object(Ask, '_generate_indicies', new_callable=AsyncMock) as mock_generate,
        patch.object(Ask, '_query_index_db', new_callable=AsyncMock) as mock_query,
    ):
        # Mock return values
        mock_direction.return_value = {
            '_retrieve_gen_conversation_direction': {'conversation_direction': 'this is the conversation direction'}
        }
        mock_analyze.return_value = {'type': 'engram', 'complexity': 'simple'}
        mock_generate.return_value = {
            'simplified_prompt': 'User wants a recipe for queso',
            'keyword_prompt': 'recipe for queso',
            'indices': ['a recipe for queso'],
        }
        mock_query.return_value = [9, 20, 4]

        # Run the method
        ask.get_sources(mock_service)

        # Allow event loop to process async calls
        await mock_direction()
        await mock_analyze()
        await mock_generate()
        await mock_query()

        # Verify how many times submit_async_tasks was called
        assert mock_service.submit_async_tasks.call_count == 3

        # Ensure each future completed successfully
        for future in mock_service.futures:
            assert future.done()  # Now indexing is safe!

        # Verify calls to plugin_manager.get_plugin()
        mock_plugin_manager.get_plugin.assert_any_call('llm', 'retrieve_gen_conversation_direction')
        mock_plugin_manager.get_plugin.assert_any_call('llm', 'retrieve_prompt_analysis')
        mock_plugin_manager.get_plugin.assert_any_call('llm', 'retrieve_gen_index')
        mock_plugin_manager.get_plugin.assert_any_call('vector_db', 'query')
