# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import logging
from dataclasses import asdict
from typing import Any

from engramic.core.interface.db import DB
from engramic.core.process import Process


class ProcessRepository:
    CACHING_DEFAULT_SIZE = 1000

    def __init__(self, plugin: dict[str, Any], cache_size: int = 1000) -> None:
        if cache_size != ProcessRepository.CACHING_DEFAULT_SIZE:
            info = 'Process repository caching is not implemented.'
            logging.info(info)

        self.db_plugin = plugin

    def save(self, process: Process) -> None:
        self.db_plugin['func'].insert_documents(table=DB.DBTables.PROCESS, docs=[asdict(process)], args=None)

    def load(self, process_id: str) -> dict[str, Any]:
        ret: list[dict[str, Any]] = self.db_plugin['func'].fetch(table=DB.DBTables.PROCESS, ids=[process_id], args=None)
        return ret[0]

    def load_most_recent(self, count: int) -> dict[str, Any]:
        ret: list[dict[str, Any]] = self.db_plugin['func'].fetch(
            table=DB.DBTables.PROCESS, ids=None, args={'history_limit': count}
        )
        return ret[0]
