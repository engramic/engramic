# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import logging
from typing import Any

from engramic.core import Index
from engramic.core.interface.vector_db import VectorDB
from engramic.infrastructure.system.plugin_specifications import vector_db_impl


class Mock(VectorDB):
    def __init__(self, mock_data: dict[str, dict[str, Any]]):
        self.mock_data = mock_data

    @vector_db_impl
    def query(self, collection_name: str, embeddings: list[float], args: dict[str, Any]) -> dict[str, Any]:
        del collection_name, embeddings

        response_str = self.mock_data[args['mock_lookup']]
        return response_str

    @vector_db_impl
    def insert(self, collection_name: str, index_list: list[Index], obj_id: str, args: dict[str, Any]) -> None:
        del obj_id, args
        logging.info('Add %s %s.', len(index_list), collection_name)
