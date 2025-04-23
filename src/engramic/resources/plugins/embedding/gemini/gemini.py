# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.


import os
from typing import Any

from google import genai
from google.genai import types

from engramic.core.interface.embedding import Embedding
from engramic.infrastructure.system.plugin_specifications import embedding_impl


class Gemini(Embedding):
    def __init__(self) -> None:
        api_key = os.environ.get('GEMINI_API_KEY')
        self._api_client = genai.Client(api_key=api_key)

    @embedding_impl
    def gen_embed(self, strings: list[str], args: dict[str, Any]) -> dict[str, list[list[float]]]:
        del args
        result = self._api_client.models.embed_content(
            model='text-embedding-004', contents=strings, config=types.EmbedContentConfig(task_type='RETRIEVAL_QUERY')
        )

        float_ret_array = [float_array.values for float_array in result.embeddings]

        return {'embeddings_list': float_ret_array}
