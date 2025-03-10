
import pluggy
from engramic.core.vector_db import VectorDB
from typing import Any
from engramic.infrastructure.system.plugin_specifications import vector_db_impl
from engramic.core.prompt import Prompt

class Mock(VectorDB):
    @vector_db_impl
    def query(self, prompt: Prompt, **kwargs: Any) -> list:
        return [9,20,4]


pm = pluggy.PluginManager("vector_db")
pm.register(Mock())