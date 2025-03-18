# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import uuid

from cachetools import LRUCache  # type: ignore

from engramic.core.engram import Engram


class EngramRepository:
    def __init__(self, plugin_manager, cache_size=1000):
        self.db_response_plugin = plugin_manager.get_plugin('db', 'response')
        self.is_connected = self.db_response_plugin['func'].connect()

        # LRU Cache to store Engram objects
        self.cache = LRUCache(maxsize=cache_size)

    def load_batch(self, engram_id_array: list[uuid.UUID]) -> list[Engram]:
        cached_engrams: list[uuid.UUID] = []
        missing_ids: list[uuid.UUID] = []

        # Check which IDs exist in the cache
        for engram_id in engram_id_array:
            if engram_id in self.cache:
                cached_engrams.append(self.cache[engram_id])
            else:
                missing_ids.append(engram_id)

        # If all are cached, return immediately
        if not missing_ids:
            return cached_engrams

        # Fetch only missing Engrams from the database
        plugin_ret = self.db_response_plugin['func'].execute(query='load_batch', engram_array=missing_ids)

        engram_data_array = plugin_ret[0]

        # Convert database results to Engram objects
        new_engrams = []
        for engram_data in engram_data_array:
            engram = Engram(
                engram_data['location'],
                engram_data['source_id'],
                engram_data['content'],
                engram_data['is_native_source'],
                engram_data['context'],
                engram_data['meta_id'],
                engram_data['library_id'],
            )
            new_engrams.append(engram)

            # Store the new Engram in the cache
            self.cache[engram_data['id']] = engram

        # Return both cached and newly loaded Engrams
        return cached_engrams + new_engrams

    def save(self):
        error = 'Not implemented yet.'
        raise NotImplementedError(error)
