# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.
import os
import uuid
from collections.abc import Mapping, Sequence
from typing import Any, cast

import chromadb
from chromadb.config import Settings

from engramic.core.index import Index
from engramic.core.interface.vector_db import VectorDB
from engramic.infrastructure.system.plugin_specifications import vector_db_impl


class ChromaDB(VectorDB):
    DEFAULT_THRESHOLD = 0.4
    DEFAULT_N_RESULTS = 2

    def __init__(self) -> None:
        db_path = os.path.join('local_storage', 'chroma_db')

        local_storage_root_path = os.getenv('LOCAL_STORAGE_ROOT_PATH')
        if local_storage_root_path is not None:
            db_path = os.path.join(local_storage_root_path, 'chroma_db')

        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=db_path,  # Use the computed db_path
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection = {}

        # Configure HNSW parameters
        hnsw_config = {'hnsw:space': 'cosine'}

        self.collection['main'] = self.client.get_or_create_collection(name='main', metadata=hnsw_config)
        self.collection['meta'] = self.client.get_or_create_collection(name='meta', metadata=hnsw_config)

    @vector_db_impl
    def query(
        self,
        collection_name: str,
        embeddings: list[float],
        repo_filters: list[str],
        args: dict[str, Any],
        type_filters: list[str],
    ) -> dict[str, Any]:
        embeddings_typed: Sequence[float] = embeddings
        n_results = args.get('n_results', self.DEFAULT_N_RESULTS)
        threshold: float = args.get('threshold', self.DEFAULT_THRESHOLD)

        where = self._build_where_clause(repo_filters, type_filters)

        results = cast(
            dict[str, Any],
            self.collection[collection_name].query(query_embeddings=embeddings_typed, n_results=n_results, where=where),
        )

        ret_ids = self._extract_results_below_threshold(results, threshold)
        return {'query_set': ret_ids}

    def _build_repo_filter(self, repo_filters: list[str]) -> dict[str, Any] | None:
        """Build repository filter clause."""
        if not repo_filters:
            return {'null': True}

        if len(repo_filters) == 1:
            return {repo_filters[0]: True}

        metadatas = [{repo_filter: {'$eq': True}} for repo_filter in repo_filters]
        return {'$or': metadatas}

    def _build_type_filter(self, type_filters: list[str]) -> dict[str, Any] | None:
        """Build type filter clause."""
        if not type_filters:
            return None

        if len(type_filters) == 1:
            return {'type': type_filters[0]}

        type_metadatas = [{'type': {'$eq': type_filter}} for type_filter in type_filters]
        return {'$or': type_metadatas}

    def _build_where_clause(self, repo_filters: list[str], type_filters: list[str]) -> dict[str, Any] | None:
        """Combine repo and type filters into a where clause."""
        repo_where = self._build_repo_filter(repo_filters)
        type_where = self._build_type_filter(type_filters)

        if repo_where is not None and type_where is not None:
            return {'$and': [repo_where, type_where]}
        if repo_where is not None:
            return repo_where
        if type_where is not None:
            return type_where

        return None

    def _extract_results_below_threshold(self, results: dict[str, Any], threshold: float) -> list[str]:
        """Extract document IDs from results that are below the distance threshold."""
        ret_ids: list[str] = []
        distances_groups = results.get('distances') or []
        documents_groups = results.get('documents') or []

        for distances, documents in zip(distances_groups, documents_groups, strict=False):
            for distance, document in zip(distances, documents, strict=False):
                if distance < threshold and document not in ret_ids:
                    ret_ids.append(document)

        return ret_ids

    @vector_db_impl
    def insert(
        self,
        collection_name: str,
        index_list: list[Index],
        obj_id: str,
        args: dict[str, Any],
        filters: list[str],
        type_filter: str,
    ) -> None:
        # start = time.perf_counter()
        del args
        documents = []
        embeddings = []
        ids = []
        metadatas_container: list[dict[str, str | int | float | bool | None]] = []

        for embedding in index_list:
            documents.append(obj_id)
            embeddings.append(cast(Sequence[float], embedding.embedding))
            ids.append(str(uuid.uuid4()))
            metadatas: dict[str, str | int | float | bool | None] = {}

            if filters is not None:
                for filter_name in filters:
                    metadatas.update({filter_name: True})
                metadatas_container.append(metadatas)
            else:
                metadatas.update({'null': True})
                metadatas_container.append(metadatas)

            if type_filter is not None:
                metadatas.update({'type': type_filter})

        meta_datas = cast(list[Mapping[str, str | int | float | bool | None]], metadatas_container)

        self.collection[collection_name].add(
            documents=documents,
            embeddings=embeddings,
            ids=ids,
            metadatas=meta_datas,
        )

        # end = time.perf_counter()

        # print(f"Function took {end - start:.4f} seconds")
