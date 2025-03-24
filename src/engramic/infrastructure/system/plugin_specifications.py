# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.


from typing import Any

import pluggy

from engramic.core import Index, Prompt

llm_impl = pluggy.HookimplMarker('llm')
llm_spec = pluggy.HookspecMarker('llm')


class LLMSpec:
    @llm_spec
    def submit(self, llm_input_prompt: Prompt, args: dict[str, str], **kwargs: dict[str, Any]) -> dict[str, str]:
        del llm_input_prompt, args, kwargs
        """Submits an LLM request with the given prompt and arguments."""
        error_message = 'Subclasses must implement `submit`'
        raise NotImplementedError(error_message)


llm_manager = pluggy.PluginManager('llm')
llm_manager.add_hookspecs(LLMSpec)


vector_db_impl = pluggy.HookimplMarker('vector_db')
vector_db_spec = pluggy.HookspecMarker('vector_db')


class VectorDBspec:
    @vector_db_spec
    def query(self, prompt: Prompt) -> set[str]:
        del prompt
        error_message = 'Subclasses must implement `query`'
        raise NotImplementedError(error_message)

    @vector_db_spec
    def insert(self, index_list: list[Index]) -> set[str]:
        del index_list
        error_message = 'Subclasses must implement `index`'
        raise NotImplementedError(error_message)


vector_manager = pluggy.PluginManager('vector_db')
vector_manager.add_hookspecs(VectorDBspec)


db_impl = pluggy.HookimplMarker('db')
db_spec = pluggy.HookspecMarker('db')


class DBspec:
    @db_spec
    def connect(self, **kwargs: Any) -> bool:
        del kwargs
        error_message = 'Subclasses must implement `connect`'
        raise NotImplementedError(error_message)

    @db_spec
    def close(self) -> bool:
        error_message = 'Subclasses must implement `close`'
        raise NotImplementedError(error_message)

    @db_spec
    def execute(self, query: str) -> dict[Any, Any]:
        del query
        error_message = 'Subclasses must implement `execute`'
        raise NotImplementedError(error_message)

    @db_spec
    def execute_data(self, query: str, data: dict[Any, Any]) -> bool:
        del query, data
        error_message = 'Subclasses must implement `execute`'
        raise NotImplementedError(error_message)


db_manager = pluggy.PluginManager('db')
db_manager.add_hookspecs(DBspec)


embedding_impl = pluggy.HookimplMarker('embedding')
embedding_spec = pluggy.HookspecMarker('embedding')


class EmbeddingSpec:
    @embedding_spec
    def gen_embed(self, prompt: Prompt) -> set[str]:
        del prompt
        error_message = 'Subclasses must implement `embed`'
        raise NotImplementedError(error_message)


vector_manager = pluggy.PluginManager('embedding')
vector_manager.add_hookspecs(EmbeddingSpec)
