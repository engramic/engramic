# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import logging
from typing import TYPE_CHECKING, Any

from engramic.core import Engram, Meta, Response
from engramic.core.observation import Observation
from engramic.infrastructure.repository.engram_repository import EngramRepository
from engramic.infrastructure.repository.history_repository import HistoryRepository
from engramic.infrastructure.repository.meta_repository import MetaRepository
from engramic.infrastructure.repository.observation_repository import ObservationRepository
from engramic.infrastructure.system.host import Host
from engramic.infrastructure.system.plugin_manager import PluginManager
from engramic.infrastructure.system.service import Service

if TYPE_CHECKING:
    from engramic.infrastructure.system.plugin_manager import PluginManager


class StorageService(Service):
    def __init__(self, host: Host) -> None:
        super().__init__(host)
        self.plugin_manager: PluginManager = host.plugin_manager
        self.history_repository: HistoryRepository = HistoryRepository(self.plugin_manager)
        self.observation_repository: ObservationRepository = ObservationRepository(self.plugin_manager)
        self.engram_repository: EngramRepository = EngramRepository(self.plugin_manager)
        self.meta_repository: MetaRepository = MetaRepository(self.plugin_manager)
        self.engram_ctr = 0
        self.observation_ctr = 0
        self.meta_ctr = 0
        self.history_ctr = 0

    def start(self) -> None:
        self.subscribe(Service.Topic.MAIN_PROMPT_COMPLETE, self.on_prompt_complete)
        self.subscribe(Service.Topic.OBSERVATION_COMPLETE, self.on_observation_complete)
        self.subscribe(Service.Topic.ENGRAM_COMPLETE, self.on_engram_complete)
        self.subscribe(Service.Topic.META_COMPLETE, self.on_meta_complete)

    def on_engram_complete(self, engram_dict: dict[str, Any]) -> None:
        engram = self.engram_repository.load_dict(engram_dict)
        self.run_task(self.save_engram(engram))

    def on_observation_complete(self, response: Observation) -> None:
        self.run_task(self.save_observation(response))

    def on_prompt_complete(self, response_dict: dict[Any, Any]) -> None:
        response = Response(**response_dict)
        self.run_task(self.save_history(response))

    def on_meta_complete(self, meta_dict: dict[str, str]) -> None:
        meta: Meta = self.meta_repository.load(meta_dict)
        self.run_task(self.save_meta(meta))

    async def save_observation(self, response: Observation) -> None:
        self.observation_repository.save(response)
        logging.info('Storage service saving observation. %s', self.observation_ctr)
        self.observation_ctr += 1

    async def save_history(self, response: Response) -> None:
        self.history_repository.save_history(response)
        logging.info('Storage service saving history. %s', self.history_ctr)
        self.history_ctr += 1

    async def save_engram(self, engram: Engram) -> None:
        self.engram_repository.save_engram(engram)
        logging.info('Storage service saving engram. %s', self.engram_ctr)
        self.engram_ctr += 1

    async def save_meta(self, meta: Meta) -> None:
        logging.info('Storage service saving meta. %s', self.meta_ctr)
        self.meta_repository.save(meta)
        self.meta_ctr += 1
