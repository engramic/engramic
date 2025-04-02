# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from dataclasses import asdict
from typing import Any

from engramic.core.interface.db import DB
from engramic.core.response import Response


class HistoryRepository:
    def __init__(self, plugin: dict[str, Any]) -> None:
        self.db_plugin = plugin

    def save_history(self, response: Response) -> None:
        self.db_plugin['func'].insert_documents(table=DB.DBTables.HISTORY, docs=[asdict(response)], args=None)
