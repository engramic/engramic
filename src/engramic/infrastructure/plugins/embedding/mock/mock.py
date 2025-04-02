# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from typing import Any

from engramic.core.interface.embedding import Embedding
from engramic.infrastructure.system.plugin_specifications import embedding_impl


class Mock(Embedding):
    def __init__(self, mock_data: dict[str, dict[str, Any]]):
        self.mock_data = mock_data

    @embedding_impl
    def gen_embed(self, strings: list[str], args: dict[str, str]) -> dict[str, list[list[float]]]:
        del strings
        response_str: dict[str, list[list[float]]] = self.mock_data[args['mock_lookup']]
        return response_str
