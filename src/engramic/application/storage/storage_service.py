# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import logging
from typing import TYPE_CHECKING

from engramic.core.response import Response
from engramic.infrastructure.repository.history_repository import HistoryRepository
from engramic.infrastructure.system.plugin_manager import PluginManager
from engramic.infrastructure.system.service import Service

if TYPE_CHECKING:
    from engramic.infrastructure.system.plugin_manager import PluginManager


class StorageService(Service):
    def __init__(self, host) -> None:
        super().__init__(host)
        self.plugin_manager: PluginManager = host.plugin_manager
        self.history_repository: HistoryRepository = HistoryRepository(self.plugin_manager)
        self.ctr = 0

    def start(self) -> None:
        super().start()
        self.subscribe(Service.Topic.MAIN_PROMPT_COMPLETE, self.on_submit_prompt)

    def on_submit_prompt(self, response_dict):
        response = Response(**response_dict)
        self.run_task(self.save_history(response))

    async def save_history(self, response):
        self.history_repository.save_history(response)
        logging.info('Storage service saving history. %s', self.ctr)
        self.ctr += 1
