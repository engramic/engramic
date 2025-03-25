import logging
from typing import Any
from uuid import uuid4

import pluggy

from engramic.core.llm import LLM
from engramic.core.prompt import Prompt
from engramic.infrastructure.system.plugin_specifications import llm_impl
from engramic.infrastructure.system.websocket_manager import WebsocketManager


class Mock(LLM):
    @llm_impl
    def submit(self, prompt: Prompt, args: dict[str, str]) -> dict[str, Any]:
        hint = args.get('hint')
        logging.info('user prompt: %.25s...', prompt.user_input)

        if hint == 'retrieve_gen_conversation_direction':
            return {'conversation_direction': 'recipes for queso'}

        if hint == 'retrieve_prompt_analysis':
            return {'type': 'engram', 'complexity': 'simple'}

        if hint == 'retrieve_gen_index':
            return {
                'simplified_prompt': 'User wants to know what this podcast is about.',
                'keyword_prompt': 'podcast is about',
                'indices': ['Who is in the podcast?', 'What is the podcast about?'],
            }

        if hint == 'response_main':
            response_str = ['The', ' podcast', ' is', ' about', ' politics', '.']
            full_string = ''
            for token in response_str:
                full_string += token
            return {'llm_response': full_string}

        if hint == 'validate':
            full_string = f"""
[meta]
id = "{uuid4()}"
locations = []
source_ids = []
keywords = ["inflation", "investors", "biotech", "medicine"]
summary_initial = "The AllIn podcast discusses the current state of the market, biotech, and the role of government in venture capital funding."
summary_full = "The AllIn podcast discusses the current state of the market, biotech, and the role of government in venture capital funding."

[[engram]]
id = "{uuid4()}"
accuracy = 4
relevancy = 4
indices = []
meta_ids = ["a1b2c3d4-e5f6-4711-8097-92a8c3f6d5e7","c3d4e5f6-a7b8-5911-8097-92a8c3f6d5e7"]
locations = ["file:///Users/allin_podcast/episodes/167.csv","file:///Users/allin_podcast/episodes/169.csv"]
source_ids = ["770g0612-f4ab-63e5-d927-778877663333", "660f9511-e39b-52d5-c817-667766552222"]
content = "The podcast is about politics."
context = {{Title="What is this podcast about."}}
library_ids = ["f1e2d3c4-b5a6-4f78-9a0b-1c2d3e4f5a6b"]
is_native_source = false

[[engram]]
id = "{uuid4()}"
accuracy = 2
relevancy = 1
indices = []
meta_ids = ["b2c3d4e5-f6a7-4811-8097-92a8c3f6d5e7","a1b2c3d4-e5f6-4711-8097-92a8c3f6d5e7"]
locations = ["file:///Users/allin_podcast/episodes/168.csv","file:///Users/allin_podcast/episodes/167.csv"]
source_ids = ["660f9511-e39b-52d5-c817-667766552222", "550e8400-e29b-41d4-a716-446655440000"]
content = "The podcast is about tigers."
context = {{Title="What is this podcast about."}}
library_ids = ["f1e2d3c4-b5a6-4f78-9a0b-1c2d3e4f5a6b"]
is_native_source = false

[[engram]]
id = "{uuid4()}"
accuracy = 4
relevancy = 4
indices = []
meta_ids = ["c3d4e5f6-a7b8-5911-8097-92a8c3f6d5e7"]
locations = ["file:///Users/allin_podcast/episodes/169.csv"]
source_ids = ["770g0612-f4ab-63e5-d927-778877663333"]
context = {{Title="What is this podcast about."}}
content = "The podcast is about technology."
library_ids = ["f1e2d3c4-b5a6-4f78-9a0b-1c2d3e4f5a6b"]
is_native_source = false
"""
            return {'llm_response': full_string}

        if hint == 'summary':
            return {'llm_response': 'The podcast is about politics.'}

        if hint == 'gen_indices':
            return {'llm_response': ['index1', 'index2', 'index3']}
        return {}

    @llm_impl
    def submit_streaming(
        self, prompt: Prompt, args: dict[str, str], websocket_manager: WebsocketManager
    ) -> dict[str, str]:
        hint = args.get('hint')

        if hint == 'response_main':
            del prompt
            response_str = ['The', ' podcast', ' is', ' about', ' politics', '.']
            full_string = ''
            for llm_token in response_str:
                full_string += llm_token
                if llm_token != '.':
                    websocket_manager.send_message(LLM.StreamPacket(llm_token, False, ''))
                else:
                    websocket_manager.send_message(LLM.StreamPacket(llm_token, True, 'End'))
            return {'llm_response': full_string}

        return {}


pm = pluggy.PluginManager('llm')
pm.register(Mock())
