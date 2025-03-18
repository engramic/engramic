import logging

import pluggy

from engramic.core.llm import LLM
from engramic.core.prompt import Prompt
from engramic.infrastructure.system.plugin_specifications import llm_impl
from engramic.infrastructure.system.websocket_manager import WebsocketManager


class Mock(LLM):
    @llm_impl
    def submit(self, prompt: Prompt, args: dict) -> dict:
        hint = args.get('hint')
        logging.info('user prompt: %.25s...', prompt.user_input)

        if hint == 'retrieve_gen_conversation_direction':
            return {'conversation_direction': 'recipes for queso'}

        if hint == 'retrieve_prompt_analysis':
            return {'type': 'engram', 'complexity': 'simple'}

        if hint == 'retrieve_gen_index':
            return {
                'simplified_prompt': 'User wants a recipe for queso',
                'keyword_prompt': 'recipe for queso',
                'indices': ['a recipe for queso'],
            }

        if hint == 'response_main':
            response_str = ['The', ' podcast', ' is', ' about', ' politics', '.']
            full_string = ''
            for token in response_str:
                full_string += token
            return {'llm_response': full_string}

        return {}

    @llm_impl
    def submit_streaming(self, prompt: Prompt, args: dict, websocket_manager: WebsocketManager) -> dict:
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
