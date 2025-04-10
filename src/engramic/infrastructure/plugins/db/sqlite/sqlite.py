# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import json
import os
import sqlite3
from multiprocessing import Lock
from typing import Any, Final

from engramic.core.interface.db import DB
from engramic.infrastructure.system.plugin_specifications import db_impl


class Sqlite(DB):
    def __init__(self) -> None:
        self._table_name_map = {table: table.value for table in DB.DBTables}
        self.multi_process_lock = Lock()

    @db_impl
    def connect(self, args: dict[str, Any]) -> None:
        del args

        self.db_path = os.path.join('local_storage', 'sqlite', 'docs.db')
        local_storage_root_path = os.getenv('LOCAL_STORAGE_ROOT_PATH')
        if local_storage_root_path is not None:
            self.db_path = os.path.join(local_storage_root_path, 'sqlite', 'docs.db')

        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        with self.multi_process_lock:
            self.db: sqlite3.Connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.cursor: sqlite3.Cursor = self.db.cursor()

            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS engram (
                    id TEXT PRIMARY KEY,
                    data TEXT,
                    name TEXT GENERATED ALWAYS AS (json_extract(data, '$.name')) STORED
                )
            """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id TEXT PRIMARY KEY,
                    data TEXT,
                    name TEXT GENERATED ALWAYS AS (json_extract(data, '$.name')) STORED
                )
            """)
            self.cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_created_date ON history(json_extract(data, '$.created_date'))"
            )
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS meta (
                    id TEXT PRIMARY KEY,
                    data TEXT,
                    name TEXT GENERATED ALWAYS AS (json_extract(data, '$.name')) STORED
                )
            """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS observation (
                    id TEXT PRIMARY KEY,
                    data TEXT,
                    name TEXT GENERATED ALWAYS AS (json_extract(data, '$.name')) STORED
                )
            """)
            self.db.commit()

    @db_impl
    def close(self, args: dict[str, Any]) -> None:
        del args

    @db_impl
    def fetch(self, table: DB.DBTables, ids: list[str], args: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
        if table not in self._table_name_map:
            error = 'Invalid table enum value'
            raise TypeError(error)

        with self.multi_process_lock:
            table_name: Final[str] = self._table_name_map[table]

            query_select = f'SELECT id, data FROM {table_name}'
            query_id = ''
            query_order = ''
            query_limit = ''

            query_params = []

            if ids:
                placeholders = ','.join('?' for _ in ids)
                query_id = f'WHERE id IN ({placeholders})'
                query_params.extend(ids)

            if args and 'history' in args:
                query_order = "ORDER BY json_extract(data, '$.created_date') DESC"
                query_limit = f"LIMIT {args['history']}"

            # Compose final query
            assembled_query = f'{query_select} {query_id} {query_order} {query_limit}'

            if query_params:
                self.cursor.execute(assembled_query, query_params)
            else:
                self.cursor.execute(assembled_query)

            rows = self.cursor.fetchall()

        return {table_name: [json.loads(data[1]) for data in rows]}

    @db_impl
    def insert_documents(self, table: DB.DBTables, docs: list[dict[str, Any]], args: dict[str, Any]) -> None:
        del args

        with self.multi_process_lock:
            if table not in self._table_name_map:
                type_error = 'Invalid table enum value'
                raise TypeError(type_error)

            values = []
            for doc in docs:
                doc_id = doc['id']
                json_data = json.dumps(doc)
                values.append((doc_id, json_data))

            table_name: Final[str] = self._table_name_map[table]
            query = f'INSERT OR REPLACE INTO {table_name} (id, data) VALUES (?, ?)'
            self.cursor.executemany(query, values)
            self.db.commit()
