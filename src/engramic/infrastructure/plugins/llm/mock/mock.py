from typing import Any

import pluggy
from engramic.core.llm import LLM
from engramic.core.prompt import Prompt
from engramic.infrastructure.system.plugin_specifications import llm_impl


class Mock(LLM):
    @llm_impl
    def submit(self, prompt: Prompt, **kwargs: Any) -> str:
        return f"This is an LLM mock return. I might not be able to counts how many r's are in straberry, but I can at least spell potato. {prompt} {kwargs}"


pm = pluggy.PluginManager('llm')
pm.register(Mock())
