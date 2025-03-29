# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import logging

from engramic.core import Index
from engramic.core.interface.vector_db import VectorDB
from engramic.infrastructure.system.plugin_specifications import vector_db_impl


class Mock(VectorDB):
    @vector_db_impl
    def query(self, collection_name: str, embedding: list[float]) -> set[str]:
        del collection_name, embedding
        logging.info('Vector DB mock.')
        ret_list = ['d1b847da-04eb-4846-a503-512aad2706c6', '83c5f4bb-65b1-4422-80b9-45ba43d91c21']
        return set(ret_list)

    @vector_db_impl
    def insert(self, collection_name: str, index_list: list[Index], obj_id: str) -> None:
        del collection_name, obj_id
        for index in index_list:
            logging.info('Add embeddings. %s', index.embedding)
