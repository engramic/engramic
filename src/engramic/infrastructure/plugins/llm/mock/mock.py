
import pluggy
from engramic.core.llm import LLM
from typing import Any
from engramic.infrastructure.system.plugin_specifications import llm_impl
from engramic.core.prompt import Prompt

class Mock(LLM):
    @llm_impl
    def submit(self, prompt: Prompt, **kwargs: Any) -> str:
        return "This is an LLM mock return. I might not be able to counts how many r's are in straberry, but I can at least spell potato."


pm = pluggy.PluginManager("llm")
pm.register(Mock())
