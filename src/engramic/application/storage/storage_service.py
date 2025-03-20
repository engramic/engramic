# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import logging
from typing import TYPE_CHECKING, Any

from engramic.core import Observation, Response
from engramic.infrastructure.repository.history_repository import HistoryRepository
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

        self.ctr = 0

    def start(self) -> None:
        self.subscribe(Service.Topic.MAIN_PROMPT_COMPLETE, self.on_prompt_complete)
        self.subscribe(Service.Topic.CODIFY_COMPLETE, self.on_codify_complete)

    def on_codify_complete(self, response: Observation) -> None:
        self.run_task(self.save_observation(response))

    def on_prompt_complete(self, response_dict: dict[Any, Any]) -> None:
        response = Response(**response_dict)
        self.run_task(self.save_history(response))

    async def save_observation(self, response: Observation) -> None:
        self.observation_repository.save(response)
        logging.info('Storage service saving observation. %s', self.ctr)

    async def save_history(self, response: Response) -> None:
        self.history_repository.save_history(response)
        logging.info('Storage service saving history. %s', self.ctr)
        self.ctr += 1
