# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import time
import uuid
from typing import Any

from cachetools import LRUCache

from engramic.core.index import Index
from engramic.core.interface.db import DB
from engramic.core.observation import Observation
from engramic.core.response import Response
from engramic.infrastructure.repository.engram_repository import EngramRepository
from engramic.infrastructure.repository.meta_repository import MetaRepository
from engramic.infrastructure.system.observation_system import ObservationSystem


class ObservationRepository:
    def __init__(self, plugin: dict[str, Any], cache_size: int = 1000) -> None:
        self.db_plugin = plugin

        self.meta_repository = MetaRepository(plugin)
        self.engram_repository = EngramRepository(plugin)

        # LRU Cache to store Engram objects
        self.cache: LRUCache[str, Observation] = LRUCache(maxsize=cache_size)

    def load_dict(self, dict_data: dict[str, Any]) -> Observation:
        engram_list = self.engram_repository.load_batch_dict(dict_data['engram_list'])
        meta = self.meta_repository.load(dict_data['meta'])

        observation: Observation = ObservationSystem(str(uuid.uuid4()), meta, engram_list, time.time())
        return observation

    def load_toml_dict(self, toml_data: dict[str, Any]) -> ObservationSystem:
        engram_list = self.engram_repository.load_batch_dict(toml_data['engram'])
        meta = self.meta_repository.load(toml_data['meta'])

        observation = ObservationSystem(str(uuid.uuid4()), meta, engram_list)
        return observation

    def validate_toml_dict(self, toml_data: dict[str, Any]) -> bool:
        if toml_data is None:
            return False

        engrams = toml_data.get('engram')
        if not isinstance(engrams, list):
            return False

        return all(self._validate_engram(engram) for engram in engrams)

    def _validate_engram(self, engram: dict[str, Any]) -> bool:
        if not isinstance(engram.get('content'), str):
            return False
        if not isinstance(engram.get('is_native_source'), bool):
            return False

        if not engram['is_native_source']:
            if not isinstance(engram.get('locations'), list):
                return False
            if not isinstance(engram.get('source_ids'), list):
                return False
            if not isinstance(engram.get('meta_ids'), list):
                return False
            if not isinstance(engram.get('accuracy'), int):
                return False
            if not isinstance(engram.get('relevancy'), int):
                return False

        return True

    def normalize_toml_dict(self, toml_data: dict[str, Any], response: Response) -> dict[str, Any]:
        meta_id = str(uuid.uuid4())
        if toml_data['meta'].get('id') is None:
            toml_data['meta']['id'] = meta_id

        if toml_data['meta'].get('source_ids') is None:
            toml_data['meta']['source_ids'] = [response.hash]

        if toml_data['meta'].get('locations') is None:
            toml_data['meta']['locations'] = [f'llm://{response.model}']

        text = toml_data['meta']['summary_full']['text']
        toml_data['meta']['summary_full'] = Index(text, None)

        for engram_dict in toml_data['engram']:
            if engram_dict.get('id') is None:
                engram_dict['id'] = str(uuid.uuid4())

            if engram_dict.get('created_date') is None:
                engram_dict['created_date'] = int(time.time())

            if engram_dict['is_native_source'] is True:
                engram_dict['source_ids'] = [response.hash]
                engram_dict['locations'] = [f'llm://{response.model}']
                engram_dict['meta_ids'] = [meta_id]

        return toml_data

    def save(self, observation: Observation) -> bool:
        ret: bool = self.db_plugin['func'].insert_documents(
            table=DB.DBTables.OBSERVATION, query='save_observation', docs=[observation], args=None
        )
        return ret
