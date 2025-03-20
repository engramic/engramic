# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.


from typing import Any

from cachetools import LRUCache  # type: ignore

from engramic.core.engram import Engram
from engramic.core.retrieve_result import RetrieveResult
from engramic.infrastructure.system.plugin_manager import PluginManager


class EngramRepository:
    def __init__(self, plugin_manager: PluginManager, cache_size: int = 1000) -> None:
        self.db_document_plugin = plugin_manager.get_plugin('db', 'document')
        self.is_connected = self.db_document_plugin['func'].connect()

        # LRU Cache to store Engram objects
        self.cache = LRUCache(maxsize=cache_size)

    def load_dict(self, engram_dict: dict[str, Any]) -> Engram:
        return Engram(
            engram_dict['locations'],
            engram_dict['source_ids'],
            engram_dict['content'],
            engram_dict['context'],
            engram_dict['indicies'],
            engram_dict['meta_ids'],
            engram_dict['library_ids'],
        )

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
        plugin_ret = self.db_document_plugin['func'].execute(query='load_batch', engram_array=missing_ids)

        engram_data_array = plugin_ret[0]['engram']

        # Convert database results to Engram objects
        new_engrams = []
        for engram_data in engram_data_array:
            engram = Engram(
                engram_data['locations'],
                engram_data['source_ids'],
                engram_data['content'],
                engram_data['is_native_source'],
                engram_data['context'],
                engram_data['meta_ids'],
                engram_data['library_ids'],
            )
            new_engrams.append(engram)

            # Store the new Engram in the cache
            self.cache[engram_data['id']] = engram

        # Return both cached and newly loaded Engrams
        return cached_engrams + new_engrams
