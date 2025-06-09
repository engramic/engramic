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
                    data TEXT
                )
            """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id TEXT PRIMARY KEY,
                    data TEXT
                )
            """)
            self.cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_created_date ON history(json_extract(data, '$.created_date'))"
            )
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS meta (
                    id TEXT PRIMARY KEY,
                    data TEXT
                )
            """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS observation (
                    id TEXT PRIMARY KEY,
                    data TEXT
                )
            """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS document (
                    id TEXT PRIMARY KEY,
                    data TEXT
                )
            """)
            self.db.commit()

    @db_impl
    def close(self, args: dict[str, Any]) -> None:
        del args

    def make_repo_filter_sql(self, repo_ids: list[str]) -> tuple[str, list[str | int]]:
        """
        Generates SQL and parameters for filtering history rows with exactly the provided repo_ids.

        Args:
            repo_ids: List of repo_id strings to filter for.

        Returns:
            Tuple of (SQL string, parameters list)
        """
        n = len(repo_ids)
        placeholders = ', '.join('?' for _ in repo_ids)
        sql = f"""json_array_length(json_extract(data, '$.prompt.repo_ids_filters')) = ? AND (SELECT COUNT(DISTINCT value) FROM json_each(json_extract(data, '$.prompt.repo_ids_filters')) WHERE value IN ({placeholders})) = ?"""
        # Parameter order: length, *repo_ids, length again (for count comparison)
        params: list[str | int] = [n, *repo_ids, n]
        return sql, params

    @db_impl
    def fetch(self, table: DB.DBTables, ids: list[str], args: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
        if table not in self._table_name_map:
            error = 'Invalid table enum value'
            raise TypeError(error)

        with self.multi_process_lock:
            table_name: Final[str] = self._table_name_map[table]

            query_select = f'SELECT id, data FROM {table_name}'
            where_clauses: list[str] = []
            query_params: list[Any] = []

            # Filter by ids
            if ids:
                placeholders = ','.join('?' for _ in ids)
                where_clauses.append(f'id IN ({placeholders})')
                query_params.extend(ids)

            # Filter by repo_ids_filters (assumes self.make_repo_filter_sql returns ("SQL", params))
            if args and 'repo_ids_filters' in args and args['repo_ids_filters'] is not None:
                repo_ids = args['repo_ids_filters']
                sql_str, params = self.make_repo_filter_sql(repo_ids)
                where_clauses.append(sql_str)
                query_params.extend(params)

            # Build WHERE
            where = ''
            if where_clauses:
                where = 'WHERE ' + ' AND '.join(where_clauses)

            # Ordering and limits
            query_order = ''
            query_limit = ''
            if args and 'history_limit' in args:
                query_order = "ORDER BY json_extract(data, '$.created_date') DESC"
                query_limit = f"LIMIT {args['history_limit']}"

            # Assemble final query
            assembled_query = f'{query_select} {where} {query_order} {query_limit}'

            if query_params:
                self.cursor.execute(assembled_query, query_params)
            else:
                self.cursor.execute(assembled_query)

            rows = self.cursor.fetchall()

        ret = {table_name: [json.loads(data[1]) for data in rows]}
        return ret

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
