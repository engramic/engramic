# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import json
import time
import uuid
from typing import Any

from cachetools import LRUCache

from engramic.core.index import Index
from engramic.core.interface.db import DB
from engramic.core.meta import Meta
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

        observation: Observation = ObservationSystem(
            dict_data['id'], meta, engram_list, time.time(), dict_data['parent_id'], dict_data['tracking_id']
        )
        return observation

    def load_toml_dict(self, toml_data: dict[str, Any]) -> ObservationSystem:
        engram_list = self.engram_repository.load_batch_dict(toml_data['engram'])
        meta = self.meta_repository.load(toml_data['meta'])
        parent_id = toml_data['parent_id']
        tracking_id = toml_data['tracking_id']

        observation = ObservationSystem(
            str(uuid.uuid4()), meta, engram_list, parent_id=parent_id, tracking_id=tracking_id
        )
        return observation

    def validate_toml_dict(self, toml_data: dict[str, Any]) -> bool:
        if toml_data is None:
            return False

        engrams = toml_data.get('engram')
        if not isinstance(engrams, list):
            return False

        meta = toml_data.get('meta')
        if not meta or 'keywords' not in meta or 'summary_full' not in meta:
            return False

        return all(self._validate_engram(engram) for engram in engrams)

    def _validate_engram(self, engram: dict[str, Any]) -> bool:
        return (
            isinstance(engram.get('content'), str)
            and ('locations' not in engram or isinstance(engram['locations'], list))
            and ('source_ids' not in engram or isinstance(engram['source_ids'], list))
            and ('meta_ids' not in engram or isinstance(engram['meta_ids'], list))
            and ('accuracy' not in engram or isinstance(engram['accuracy'], int))
            and ('relevancy' not in engram or isinstance(engram['relevancy'], int))
        )

    def normalize_toml_dict(self, toml_data: dict[str, Any], response: Response) -> dict[str, Any]:
        meta_id = self._normalize_meta(toml_data['meta'], response)
        for engram_dict in toml_data['engram']:
            self._normalize_engram(engram_dict, meta_id, response)

        toml_data['parent_id'] = response.prompt.prompt_id
        toml_data['tracking_id'] = response.prompt.tracking_id
        return toml_data

    def _normalize_meta(self, meta: dict[str, Any], response: Response) -> Any:
        meta_id = str(uuid.uuid4())
        meta.setdefault('type', Meta.SourceType.RESPONSE.value)
        meta.setdefault('id', meta_id)
        meta.setdefault('source_ids', [response.source_id])
        meta.setdefault('locations', [f'llm://{response.source_id}'])
        meta.setdefault('repo_ids', response.prompt.repo_ids_filters)

        # Normalize summary_full into Index
        text = meta.get('summary_full', {}).get('text', '')
        meta['summary_full'] = Index(text, None)

        return meta['id']

    def _normalize_engram(self, engram: dict[str, Any], meta_id: str, response: Response) -> None:
        engram.setdefault('id', str(uuid.uuid4()))
        engram.setdefault('created_date', int(time.time()))
        engram.setdefault('source_ids', [response.id])
        engram.setdefault('locations', [f'llm://{response.model}'])
        engram.setdefault('meta_ids', [meta_id])
        engram.setdefault('is_native_source', False)
        if engram['context']:
            try:
                engram['context'] = json.loads(engram['context'])
            except json.JSONDecodeError as e:
                error = (
                    f"Failed to decode JSON in 'context' in Normalize Engram (a formatting issue with LLM output): {e}"
                )
                raise RuntimeError(error) from e

    def save(self, observation: Observation) -> bool:
        ret: bool = self.db_plugin['func'].insert_documents(
            table=DB.DBTables.OBSERVATION, query='save_observation', docs=[observation], args=None
        )
        return ret
