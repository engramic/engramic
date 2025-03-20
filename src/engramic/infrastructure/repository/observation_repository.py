# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import uuid
from typing import Any

from cachetools import LRUCache  # type: ignore

from engramic.core.observation import Observation
from engramic.infrastructure.repository.engram_repository import EngramRepository
from engramic.infrastructure.repository.meta_repository import MetaRepository
from engramic.infrastructure.system.plugin_manager import PluginManager


class ObservationRepository:
    RELEVANCE_CONSTANT = 3
    ACCURACY_CONSTANT = 3

    def __init__(self, plugin_manager: PluginManager, cache_size: int = 1000) -> None:
        self.db_plugin = plugin_manager.get_plugin('db', 'document')
        self.is_connected = self.db_plugin['func'].connect()
        self.meta_repository = MetaRepository(plugin_manager)
        self.engram_repository = EngramRepository(plugin_manager)

        # LRU Cache to store Engram objects
        self.cache = LRUCache(maxsize=cache_size)

    def load_toml_file(self, toml_data: dict[str, Any]) -> Observation:
        filtered_engrams_dict = [
            {
                key: value
                for key, value in {**m, 'is_native_source': False}.items()
                if key not in {'accuracy', 'relevance'}
            }
            for m in toml_data['engram']
            if m['accuracy'] > ObservationRepository.ACCURACY_CONSTANT
            and m['relevance'] > ObservationRepository.RELEVANCE_CONSTANT
        ]

        combined_source_ids = list({source_id for m in filtered_engrams_dict for source_id in m['source_ids']})
        combined_locations = list({location for m in filtered_engrams_dict for location in m['locations']})

        toml_data['meta'][0]['id'] = str(uuid.uuid4())
        toml_data['meta'][0]['source_ids'] = combined_source_ids
        toml_data['meta'][0]['locations'] = combined_locations

        filtered_engram_list = self.engram_repository.load_batch_dict(filtered_engrams_dict)
        meta = self.meta_repository.load(toml_data['meta'][0])

        observation = Observation(str(uuid.uuid4()), meta, filtered_engram_list)
        return observation

    def save(self, observation: Observation) -> bool:
        ret: bool = self.db_plugin['func'].execute_data(query='save_observation', data=observation)
        return ret
