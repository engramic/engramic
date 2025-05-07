# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.


from dataclasses import dataclass
from typing import Any

from engramic.core.host import Host
from engramic.infrastructure.system.service import Service


class ProgressService(Service):
    """
    Tracks and manages the processing progress of inputs (currently prompts and documents) within the Engramic system.

    This service listens for events related to engram and index creation, maintaining counters
    that reflect the processing state of each input. Once all expected engrams and indices are
    inserted, it emits a completion event for that input.

    Attributes:
        inputs (dict[str, InputProgress]): A mapping of input IDs to their corresponding progress state.

    Inner Classes:
        InputProgress (dataclass): Tracks per-input counters for engrams and indices:
            - engram_ctr (int | None): Total engrams created for the input.
            - index_created_ctr (int | None): Number of index creation operations triggered.
            - index_ctr (int | None): Total indices expected for the input.
            - index_insert_ctr (int | None): Number of successfully inserted indices.

    Methods:
        init_async(): Asynchronously initializes the service.
        start(): Subscribes to system events relevant to input tracking and begins the service.
        on_input_create(msg: dict): Initializes progress tracking for a new input.
        on_engram_created(msg: dict): Increments the engram counter for the associated input.
        on_index_created(msg: dict): Updates index creation and expected index count for the input.
        _on_index_inserted(msg: dict): Increments the inserted index count and checks for input completion.
    """

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
