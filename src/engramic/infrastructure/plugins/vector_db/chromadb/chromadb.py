# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.
import uuid
from collections.abc import Sequence
from typing import cast

import chromadb

from engramic.core.index import Index
from engramic.core.interface.vector_db import VectorDB
from engramic.infrastructure.system.plugin_specifications import vector_db_impl


class ChromaDB(VectorDB):
    def __init__(self) -> None:
        self.threshold = 0.5
        self.client = chromadb.PersistentClient(path='local_storage/chroma_db')
        self.collection = {}
        self.collection['main'] = self.client.get_or_create_collection(name='main')
        self.collection['meta'] = self.client.get_or_create_collection(name='meta')

    @vector_db_impl
    def query(self, collection_name: str, embedding: list[float]) -> set[str]:
        embedding_type: Sequence[float] = embedding
        results = self.collection[collection_name].query(query_embeddings=[embedding_type], n_results=2)

        distances = cast(list[list[float]], results['distances'])[0]
        documents = cast(list[list[str]], results['documents'])[0]

        ret_ids = []
        for i, distance in enumerate(distances):
            if distance > self.threshold:
                ret_ids.append(documents[i])

        return set(ret_ids)

    @vector_db_impl
    def insert(self, collection_name: str, index_list: list[Index], obj_id: str) -> None:
        documents = []
        embeddings = []
        ids = []

        for embedding in index_list:
            documents.append(obj_id)
            embeddings.append(cast(Sequence[float], embedding.embedding))
            ids.append(str(uuid.uuid4()))

        self.collection[collection_name].add(documents=documents, embeddings=embeddings, ids=ids)

        # collection = self.collection[collection_name].get()
