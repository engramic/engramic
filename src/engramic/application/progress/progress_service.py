# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.


from dataclasses import dataclass
from typing import Any

from engramic.core.host import Host
from engramic.infrastructure.system.service import Service


class ProgressService(Service):
    @dataclass
    class InputProgress:
        engram_ctr: int | None = 0
        index_created_ctr: int | None = 0
        index_ctr: int | None = 0
        index_insert_ctr: int | None = 0

    def __init__(self, host: Host) -> None:
        super().__init__(host)
        self.inputs: dict[str, Any] = {}

    def init_async(self) -> None:
        return super().init_async()

    def start(self) -> None:
        self.subscribe(Service.Topic.INPUT_CREATED, self.on_input_create)
        self.subscribe(Service.Topic.ENGRAM_CREATED, self.on_engram_created)
        self.subscribe(Service.Topic.INDEX_CREATED, self.on_index_created)
        self.subscribe(Service.Topic.INDEX_INSERTED, self._on_index_inserted)
        super().start()

    def on_input_create(self, msg: dict[Any, Any]) -> None:
        input_id = msg['input_id']
        self.inputs[input_id] = ProgressService.InputProgress()

    def on_engram_created(self, msg: dict[Any, Any]) -> None:
        input_id = msg['input_id']
        counter = msg['count']

        if input_id in self.inputs:
            input_process = self.inputs[input_id]
            input_process.engram_ctr += counter

    def on_index_created(self, msg: dict[Any, Any]) -> None:
        input_id = msg['input_id']
        counter = msg['count']

        if input_id in self.inputs:
            document_process = self.inputs[input_id]
            document_process.index_ctr += counter
            document_process.index_created_ctr += 1

    def _on_index_inserted(self, msg: dict[Any, Any]) -> None:
        input_id = msg['input_id']
        counter = msg['count']

        if input_id in self.inputs:
            input_process = self.inputs[input_id]
            input_process.index_insert_ctr += counter

            if (
                input_process.engram_ctr == input_process.index_created_ctr
                and input_process.index_ctr == input_process.index_insert_ctr
            ):
                self.send_message_async(Service.Topic.INPUT_COMPLETED, {'input_id': input_id})
