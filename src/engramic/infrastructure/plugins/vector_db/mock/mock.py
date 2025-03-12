import logging
from typing import Any

import pluggy
from engramic.core.prompt import Prompt
from engramic.core.vector_db import VectorDB
from engramic.infrastructure.system.plugin_specifications import vector_db_impl


class Mock(VectorDB):
    @vector_db_impl
    def query(self, prompt: Prompt, **kwargs: Any) -> list:
        logging.info('Vector DB mock.%s %s', prompt, kwargs)
        return [9, 20, 4]


pm = pluggy.PluginManager('vector_db')
pm.register(Mock())
