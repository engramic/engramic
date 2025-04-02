# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.


from dataclasses import asdict
from typing import Any

from cachetools import LRUCache

from engramic.core import Index, Meta
from engramic.core.interface.db import DB


class MetaRepository:
    def __init__(self, plugin: dict[str, Any], cache_size: int = 1000) -> None:
        self.db_plugin = plugin

        # LRU Cache to store Engram objects
        self.cache: LRUCache[str, Meta] = LRUCache(maxsize=cache_size)

    def save(self, meta: Meta) -> None:
        self.db_plugin['func'].insert_documents(table=DB.DBTables.META, docs=[asdict(meta)], args=None)

    def load(self, meta_dict: dict[str, Any]) -> Meta:
        if isinstance(meta_dict.get('summary_full'), dict):
            summary = meta_dict['summary_full']
            meta_dict['summary_full'] = Index(summary['text'], summary['embedding'])
        meta = Meta(**meta_dict)
        return meta

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

        # Fetch only missing Meta from the database
        plugin_ret = self.db_plugin['func'].fetch(table=DB.DBTables.META, ids=missing_ids, args=None)

        meta_data_array = plugin_ret[0]['meta']

        # Convert database results to Engram objects
        new_metas = []
        for meta_data in meta_data_array:
            index = Index(**meta_data['summary_full'])
            meta = Meta(
                meta_data['id'],
                meta_data['locations'],
                meta_data['source_ids'],
                meta_data['keywords'],
                meta_data['summary_initial'],
                index,
            )

            new_metas.append(meta)

            # Store the new Engram in the cache
            self.cache[meta_data['id']] = meta

        # Return both cached and newly loaded Engrams
        return cached_metas + new_metas
