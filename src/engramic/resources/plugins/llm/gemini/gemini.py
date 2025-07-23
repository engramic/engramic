# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import base64
import json
import logging
import os
import re
from typing import Any, cast, no_type_check

from google import genai
from google.genai import types
from pydantic import BaseModel, create_model

from engramic.core.interface.llm import LLM
from engramic.core.prompt import Prompt
from engramic.infrastructure.system.plugin_specifications import llm_impl
from engramic.infrastructure.system.websocket_manager import WebsocketManager

logging.getLogger('google_genai').setLevel(logging.WARNING)
logging.getLogger('httpx').setLevel(logging.WARNING)


class Gemini(LLM):
    def __init__(self) -> None:
        api_key = os.environ.get('GEMINI_API_KEY')
        self._api_client = genai.Client(api_key=api_key)

    @no_type_check
    def create_pydantic_model(self, name: str, fields: dict[str, type[Any]]) -> type[BaseModel]:
        model_fields = {key: (field_type, ...) for key, field_type in fields.items()}
        model: Any = create_model(name, **model_fields)
        return cast(type[BaseModel], model)

    def extract_toml_block(self, ret_string: str) -> str:
        # Step 1: Remove the first ```toml (and any whitespace after)
        ret_string = re.sub(r'^```toml\s*', '', ret_string.strip())

        # Step 2: Remove the last closing ```
        ret_string = re.sub(r'```$', '', ret_string.strip())

        return ret_string.strip()

    @llm_impl
    def submit(
        self, prompt: Prompt, images: list[str], structured_schema: dict[str, Any], args: dict[str, Any]
    ) -> dict[str, Any]:
        model = args['model']

        parts = [types.Part.from_text(text=prompt.render_prompt())]

        if images:
            parts.extend([
                types.Part.from_bytes(mime_type='image/png', data=base64.b64decode(image_b64)) for image_b64 in images
            ])

        contents = [
            types.Content(
                parts=parts,
            ),
        ]

        temperature = 0.5
        top_p = 0.5
        top_k = 30

        if 'deterministic' in args and (not args.get('deterministic') or args['deterministic'].lower() == 'true'):
            temperature = 0.01
            top_p = 1
            top_k = 1

        # Pre-define values
        max_output_tokens = 8192
        response_mime_type = 'text/plain'
        response_schema = None

        # Structured response case
        if structured_schema is not None:
            pydantic_model = self.create_pydantic_model('dynamic_model', structured_schema)
            response_schema = pydantic_model
            response_mime_type = 'application/json'

        # Model-specific config
        config_kwargs = {
            'temperature': temperature,
            'top_p': top_p,
            'top_k': top_k,
            'max_output_tokens': max_output_tokens,
            'response_mime_type': response_mime_type,
            'response_schema': response_schema,
        }

        if model in {'gemini-2.5-flash-preview-04-17', 'gemini-2.5-flash', 'gemini-2.5-pro'}:
            config_kwargs['thinking_config'] = types.ThinkingConfig(include_thoughts=False, thinking_budget=128)

        # Construct config explicitly
        generate_content_config = types.GenerateContentConfig(
            temperature=config_kwargs['temperature'],
            top_p=config_kwargs['top_p'],
            top_k=config_kwargs['top_k'],
            max_output_tokens=config_kwargs['max_output_tokens'],
            response_mime_type=config_kwargs['response_mime_type'],
            thinking_config=config_kwargs.get('thinking_config'),
            response_schema=config_kwargs['response_schema'],
        )

        response = self._api_client.models.generate_content(
            model=model, contents=contents, config=generate_content_config
        )

        # finish_reason = response.candidates[0].finish_reason

        if response.text is None:
            finish_reason = 'Not Given.'
            if hasattr(response, 'candidates') and response.candidates and len(response.candidates) > 0:
                finish_reason = str(response.candidates[0].finish_reason)
            error = f'Error in Gemini submit. Response.text is None. Finish Reason: {finish_reason}'
            raise RuntimeError(error)

        ret_string: str = str(response.text)

        return {'llm_response': self.extract_toml_block(ret_string)}

    @llm_impl
    def submit_streaming(
        self, prompt: Prompt, args: dict[str, Any], websocket_manager: WebsocketManager
    ) -> dict[str, str]:
        model = args['model']
        contents = [
            types.Content(
                parts=[
                    types.Part.from_text(text=prompt.render_prompt()),
                ],
            ),
        ]

        temperature = 0.5
        top_p = 0.5
        top_k = 30
        max_output_tokens = 8192
        response_mime_type = 'text/plain'

        thinking_budget = 0
        if 'thinking_budget' in args:
            thinking_budget = args['thinking_budget'] * 10000

        if model == 'gemini-2.5-pro':
            thinking_budget = 300

        thinking_config = None
        if model in {'gemini-2.5-flash-preview-04-17', 'gemini-2.5-flash', 'gemini-2.5-pro'}:
            thinking_config = types.ThinkingConfig(include_thoughts=False, thinking_budget=thinking_budget)

        generate_content_config = types.GenerateContentConfig(
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            max_output_tokens=max_output_tokens,
            response_mime_type=response_mime_type,
            thinking_config=thinking_config,
        )

        response = self._api_client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        )

        response_id = args['response_id']
        repo_ids_filters = args['repo_ids_filters']
        packet = LLM.StreamPacket(
            f'{{"response_id":"{response_id}","repo_ids_filters":{json.dumps(repo_ids_filters)}}}', False, ''
        )
        websocket_manager.send_message(packet)

        full_response = ''
        for chunk in response:
            if chunk.text is None:
                finish_reason = 'Not Given.'
                if hasattr(chunk, 'candidates') and chunk.candidates and len(chunk.candidates) > 0:
                    finish_reason = str(chunk.candidates[0].finish_reason)
                error = f'Error in Gemini submit. Response.text is None. Finish Reason: {finish_reason}'
                logging.warning(error)
            if chunk.text:
                websocket_manager.send_message(LLM.StreamPacket(chunk.text, False, ''))

            if chunk.text:
                full_response += chunk.text

        websocket_manager.send_message(LLM.StreamPacket('{"response_end":"true"}', False, ''))

        return {'llm_response': self.extract_toml_block(full_response)}
