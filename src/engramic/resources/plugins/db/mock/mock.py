# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from typing import Any

from engramic.core.interface.db import DB
from engramic.infrastructure.system.plugin_specifications import db_impl


class Mock(DB):
    def __init__(self, mock_data: dict[str, dict[str, Any]]) -> None:
        self.mock_data = mock_data
        self.observations: dict[str, Any] = {}
        self.history: dict[str, Any] = {}
        self.engrams: dict[str, Any] = {}
        self.metas: dict[str, Any] = {}

    @db_impl
    def connect(self, args: dict[str, Any]) -> None:
        del args

    @db_impl
    def close(self, args: dict[str, Any]) -> None:
        del args

    @db_impl
    def fetch(self, table: DB.DBTables, ids: list[str], args: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
        del args

        if table.value == 'history':
            return {'history': [self.history[id_] for id_ in ids]}
        if table.value == 'observation':
            return {'return_observation': [self.observations[id_] for id_ in ids]}
        if table.value == 'engram':
            return {'return_engram': [self.engrams[id_] for id_ in ids]}
        if table.value == 'meta':
            return {'return_meta': [self.metas[id_] for id_ in ids]}

        return {}

    @db_impl
    def insert_documents(self, table: DB.DBTables, docs: list[dict[str, Any]], args: dict[str, Any]) -> None:
        del args
        if table.value == 'history':
            for doc in docs:
                self.history[doc['id']] = doc
        elif table.value == 'observation':
            for doc in docs:
                self.observations[doc['id']] = doc
        elif table.value == 'engram':
            for doc in docs:
                self.engrams[doc['id']] = doc
        elif table.value == 'meta':
            for doc in docs:
                self.metas[doc['id']] = doc
