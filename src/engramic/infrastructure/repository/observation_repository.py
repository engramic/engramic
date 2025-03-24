# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import uuid
from typing import Any

from cachetools import LRUCache

from engramic.core.observation import Observation
from engramic.infrastructure.repository.engram_repository import EngramRepository
from engramic.infrastructure.repository.meta_repository import MetaRepository
from engramic.infrastructure.system.observation_system import ObservationSystem
from engramic.infrastructure.system.plugin_manager import PluginManager


class ObservationRepository:
    def __init__(self, plugin_manager: PluginManager, cache_size: int = 1000) -> None:
        self.db_plugin = plugin_manager.get_plugin('db', 'document')
        self.is_connected = self.db_plugin['func'].connect()
        self.meta_repository = MetaRepository(plugin_manager)
        self.engram_repository = EngramRepository(plugin_manager)

        # LRU Cache to store Engram objects
        self.cache: LRUCache[str, Observation] = LRUCache(maxsize=cache_size)

    def load_dict(self, dict_data: dict[str, Any]) -> Observation:
        engram_list = self.engram_repository.load_batch_dict(dict_data['engram_list'])
        meta = self.meta_repository.load(dict_data['meta'])

        observation = ObservationSystem(str(uuid.uuid4()), meta, engram_list)
        return observation

    def load_toml_dict(self, toml_data: dict[str, Any]) -> ObservationSystem:
        engram_list = self.engram_repository.load_batch_dict(toml_data['engram'])
        meta = self.meta_repository.load(toml_data['meta'])

        observation = ObservationSystem(str(uuid.uuid4()), meta, engram_list)
        return observation

    def save(self, observation: Observation) -> bool:
        ret: bool = self.db_plugin['func'].execute_data(query='save_observation', data=observation)
        return ret
