# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.


from typing import Any

import pluggy

from engramic.core import Index, Prompt
from engramic.core.interface.db import DB
from engramic.core.interface.embedding import Embedding
from engramic.core.interface.llm import LLM
from engramic.core.interface.vector_db import VectorDB

llm_impl = pluggy.HookimplMarker('llm')
llm_spec = pluggy.HookspecMarker('llm')


class LLMSpec(LLM):
    @llm_spec
    def submit(self, prompt: Prompt, structured_schema: dict[str, Any], args: dict[str, Any]) -> dict[str, str]:
        del prompt, structured_schema, args
        """Submits an LLM request with the given prompt and arguments."""
        error_message = 'Subclasses must implement `submit`'
        raise NotImplementedError(error_message)


llm_manager = pluggy.PluginManager('llm')
llm_manager.add_hookspecs(LLMSpec)


vector_db_impl = pluggy.HookimplMarker('vector_db')
vector_db_spec = pluggy.HookspecMarker('vector_db')


class VectorDBspec(VectorDB):
    @vector_db_spec
    def query(self, collection_name: str, embeddings: list[float], args: dict[str, Any]) -> dict[str, Any]:
        del embeddings, collection_name, args
        error_message = 'Subclasses must implement `query`'
        raise NotImplementedError(error_message)

    @vector_db_spec
    def insert(self, collection_name: str, index_list: list[Index], obj_id: str, args: dict[str, Any]) -> None:
        del index_list, collection_name, obj_id, args
        error_message = 'Subclasses must implement `index`'
        raise NotImplementedError(error_message)


vector_manager = pluggy.PluginManager('vector_db')
vector_manager.add_hookspecs(VectorDBspec)


db_impl = pluggy.HookimplMarker('db')
db_spec = pluggy.HookspecMarker('db')


class DBspec(DB):
    @db_spec
    def connect(self, args: dict[str, Any]) -> None:
        del args
        error_message = 'Subclasses must implement `connect`'
        raise NotImplementedError(error_message)

    @db_spec
    def close(self, args: dict[str, Any]) -> None:
        del args
        error_message = 'Subclasses must implement `close`'
        raise NotImplementedError(error_message)

    @db_spec
    def fetch(self, table: DB.DBTables, ids: list[str], args: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
        del table, ids, args
        error_message = 'Subclasses must implement `execute`'
        raise NotImplementedError(error_message)

    @db_spec
    def insert_documents(self, table: DB.DBTables, docs: list[dict[str, Any]], args: dict[str, Any]) -> None:
        del table, docs, args
        error_message = 'Subclasses must implement `execute_data`'
        raise NotImplementedError(error_message)


db_manager = pluggy.PluginManager('db')
db_manager.add_hookspecs(DBspec)


embedding_impl = pluggy.HookimplMarker('embedding')
embedding_spec = pluggy.HookspecMarker('embedding')


class EmbeddingSpec(Embedding):
    @embedding_spec
    def gen_embed(self, strings: list[str], args: dict[str, Any]) -> dict[str, list[list[float]]]:
        del strings, args
        error_message = 'Subclasses must implement `embed`'
        raise NotImplementedError(error_message)


vector_manager = pluggy.PluginManager('embedding')
vector_manager.add_hookspecs(EmbeddingSpec)
