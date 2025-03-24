# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from typing import TYPE_CHECKING, Any

from engramic.application.retrieve.ask import Ask
from engramic.core import Index, Prompt
from engramic.infrastructure.system.host import Host
from engramic.infrastructure.system.service import Service

if TYPE_CHECKING:
    from engramic.infrastructure.system.plugin_manager import PluginManager


class RetrieveService(Service):
    # ITERATIONS = 3

    def __init__(self, host: Host) -> None:
        super().__init__(host)
        self.plugin_manager: PluginManager = host.plugin_manager
        self.vector_db_plugin = self.plugin_manager.get_plugin('vector_db', 'db')

    def start(self) -> None:
        self.subscribe(Service.Topic.SUBMIT_PROMPT, self.on_submit_prompt)
        self.subscribe(Service.Topic.INDEX_COMPLETE, self.on_index_complete)

    # when called from monitor service
    def on_submit_prompt(self, data: str) -> None:
        self.submit(Prompt(data))

    # when used from main
    def submit(self, prompt: Prompt) -> None:
        retrieval = Ask(prompt, self.plugin_manager, self)
        retrieval.get_sources()

    def on_index_complete(self, index_message: dict[str, Any]) -> None:
        raw_index: list[dict[str, str]] = index_message['index']
        index_list = [Index(**item) for item in raw_index]
        self.run_task(self.insert_vector(index_list))

    async def insert_vector(self, index_list: list[Index]) -> None:
        args = self.vector_db_plugin['args']
        self.vector_db_plugin['func'].insert(index_list=index_list, args=args)
