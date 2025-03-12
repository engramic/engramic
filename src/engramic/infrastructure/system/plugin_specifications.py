# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.


import pluggy
from engramic.core.prompt import Prompt

llm_impl = pluggy.HookimplMarker('llm')
llm_spec = pluggy.HookspecMarker('llm')


class LLMSpec:
    @llm_spec
    def submit(self, llm_input_prompt: Prompt, args: dict) -> dict:
        del llm_input_prompt, args
        """Submits an LLM request with the given prompt and arguments."""
        error_message = 'Subclasses must implement `submit`'
        raise NotImplementedError(error_message)


llm_manager = pluggy.PluginManager('llm')
llm_manager.add_hookspecs(LLMSpec)


vector_db_impl = pluggy.HookimplMarker('vector_db')
vector_db_spec = pluggy.HookspecMarker('vector_db')


class VectorDBspec:
    @vector_db_spec
    def query(self, prompt: Prompt) -> set:
        del prompt
        """Submits an LLM request with the given prompt and arguments."""
        error_message = 'Subclasses must implement `query`'
        raise NotImplementedError(error_message)


vector_manager = pluggy.PluginManager('vector_db')
vector_manager.add_hookspecs(VectorDBspec)
