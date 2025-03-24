# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.


from typing import Any

from cachetools import LRUCache

from engramic.core.meta import Meta
from engramic.infrastructure.system.plugin_manager import PluginManager


class MetaRepository:
    def __init__(self, plugin_manager: PluginManager, cache_size: int = 1000) -> None:
        self.db_plugin = plugin_manager.get_plugin('db', 'document')
        self.is_connected = self.db_plugin['func'].connect()

        # LRU Cache to store Engram objects
        self.cache: LRUCache[str, Meta] = LRUCache(maxsize=cache_size)

    def save(self, meta: Meta) -> None:
        self.db_plugin['func'].execute_data(query='save_meta', data=meta)

    def load(self, meta_dict: dict[str, Any]) -> Meta:
        return Meta(**meta_dict)

    def load_batch(self, meta_array: list[str]) -> list[Meta]:
        cached_metas: list[Meta] = []
        missing_ids: list[str] = []

        # Check which IDs exist in the cache
        for meta_id in meta_array:
            if meta_id in self.cache:
                cached_metas.append(self.cache[meta_id])
            else:
                missing_ids.append(meta_id)

        # If all are cached, return immediately
        if not missing_ids:
            return cached_metas

        # Fetch only missing Engrams from the database
        plugin_ret = self.db_plugin['func'].execute(query='load_batch_meta', meta_array=missing_ids)

        meta_data_array = plugin_ret[0]['meta']

        # Convert database results to Engram objects
        new_metas = []
        for meta_data in meta_data_array:
            meta = Meta(
                meta_data['id'],
                meta_data['location'],
                meta_data['source_id'],
                meta_data['keywords'],
                meta_data['summary_initial'],
                meta_data['summary_full'],
            )

            new_metas.append(meta)

            # Store the new Engram in the cache
            self.cache[meta_data['id']] = meta

        # Return both cached and newly loaded Engrams
        return cached_metas + new_metas
