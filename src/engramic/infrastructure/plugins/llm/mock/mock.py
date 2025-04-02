# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import re
from typing import Any

from engramic.core.interface.llm import LLM
from engramic.core.prompt import Prompt
from engramic.infrastructure.system.plugin_specifications import llm_impl
from engramic.infrastructure.system.websocket_manager import WebsocketManager


class Mock(LLM):
    def __init__(self, mock_data: dict[str, dict[str, Any]]):
        self.mock_data = mock_data

    @llm_impl
    def submit(self, prompt: Prompt, structured_schema: dict[str, Any], args: dict[str, Any]) -> dict[str, Any]:
        del structured_schema, prompt

        response_str: dict[str, Any] = self.mock_data[args['mock_lookup']]
        return response_str

    @llm_impl
    def submit_streaming(
        self, prompt: Prompt, args: dict[str, Any], websocket_manager: WebsocketManager
    ) -> dict[str, str]:
        del prompt
        full_string = self.mock_data[args['mock_lookup']]

        response_str = re.split(r'(\s+)', full_string['llm_response'])
        for llm_token in response_str:
            if llm_token != '.':
                websocket_manager.send_message(LLM.StreamPacket(llm_token, False, ''))
            else:
                websocket_manager.send_message(LLM.StreamPacket(llm_token, True, 'End'))

        return full_string
