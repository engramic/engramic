# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.


from dataclasses import asdict
from typing import Any

from cachetools import LRUCache

from engramic.core.engram import Engram
from engramic.core.index import Index
from engramic.core.interface.db import DB
from engramic.core.retrieve_result import RetrieveResult


class EngramRepository:
    def __init__(self, plugin: dict[str, Any], cache_size: int = 1000) -> None:
        self.db_plugin = plugin

        # LRU Cache to store Engram objects
        self.cache: LRUCache[str, Engram] = LRUCache(maxsize=cache_size)

    def save_engram(self, engram: Engram) -> None:
        self.db_plugin['func'].insert_documents(table=DB.DBTables.ENGRAM, docs=[asdict(engram)], args=None)

    def load_dict(self, engram_dict: dict[str, Any]) -> Engram:
        engram = Engram(**engram_dict)

        return engram

    def load_batch_dict(self, dict_list: list[dict[str, str]]) -> list[Engram]:
        return [self.load_dict(engram_dict) for engram_dict in dict_list]

    def load_batch_retrieve_result(self, retrieve_result: RetrieveResult) -> list[Engram]:
        cached_engrams: list[Engram] = []
        missing_ids: list[str] = []

        # Check which IDs exist in the cache
        for engram_id in retrieve_result.engram_id_array:
            if engram_id in self.cache:
                cached_engrams.append(self.cache[engram_id])
            else:
                missing_ids.append(engram_id)

        # If all are cached, return immediately
        if not missing_ids:
            return cached_engrams

        # Fetch only missing Engrams from the database
        plugin_ret = self.db_plugin['func'].fetch(table=DB.DBTables.ENGRAM, ids=missing_ids, args=None)

        engram_data_array = plugin_ret[0]['engram']

        # Convert database results to Engram objects
        new_engrams = []
        for engram_data in engram_data_array:
            indices = engram_data['indices']
            engram_data['indices'] = [Index(**d) for d in indices]
            engram = Engram(**engram_data)
            new_engrams.append(engram)

            # Store the new Engram in the cache
            self.cache[engram_data['id']] = engram

        # Return both cached and newly loaded Engrams
        return cached_engrams + new_engrams
