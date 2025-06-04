# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import logging
from dataclasses import asdict
from typing import Any

from engramic.core.document import Document
from engramic.core.interface.db import DB


class DocumentRepository:
    CACHING_DEFAULT_SIZE = 1000

    def __init__(self, plugin: dict[str, Any], cache_size: int = 1000) -> None:
        if cache_size != DocumentRepository.CACHING_DEFAULT_SIZE:
            info = 'Document repository caching is not implemented.'
            logging.info(info)

        self.db_plugin = plugin

    def save(self, document: Document) -> None:
        self.db_plugin['func'].insert_documents(table=DB.DBTables.DOCUMENT, docs=[asdict(document)], args=None)

    def load(self, document_id: str) -> dict[str, Any]:
        ret: list[dict[str, Any]] = self.db_plugin['func'].fetch(
            table=DB.DBTables.DOCUMENT, ids=[document_id], args=None
        )
        return ret[0]
