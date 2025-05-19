# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import logging
from dataclasses import dataclass, field
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
    class Progress:
        index_list: dict[Any, Any] = field(default_factory=dict)
        engram_list: dict[Any, Any] = field(default_factory=dict)
        completed: bool = False
        lesson_id = ''  # optional lesson id

    def __init__(self, host: Host) -> None:
        super().__init__(host)
        self.progress_items: dict[str, ProgressService.Progress] = {}
        self.lesson_items: dict[str, list[str]] = {}

    def init_async(self) -> None:
        return super().init_async()

    def start(self) -> None:
        self.subscribe(Service.Topic.INPUT_CREATED, self.on_input_create)
        self.subscribe(Service.Topic.ENGRAM_CREATED, self.on_engram_created)
        self.subscribe(Service.Topic.INDEX_CREATED, self.on_index_created)
        self.subscribe(Service.Topic.LESSON_CREATED, self.on_lesson_created)
        self.subscribe(Service.Topic.INDEX_INSERTED, self._on_index_inserted)
        super().start()

    def on_input_create(self, msg: dict[Any, Any], lesson_id: str | None = None) -> None:
        input_id = msg['input_id']
        input_type = msg['type']

        if input_type == 'prompt' and not lesson_id:
            return  # Not tracking prompt's that aren't part of lesson right now

        if input_id not in self.progress_items:
            self.progress_items[input_id] = ProgressService.Progress()
            if lesson_id:
                self.progress_items[input_id].lesson_id = lesson_id
                self.send_message_async(
                    Service.Topic.PROGRESS_UPDATED,
                    {'progress_type': 'lesson', 'lesson_id': lesson_id, 'percent_inputs_complete': 0.0},
                )
            else:
                self.send_message_async(
                    Service.Topic.PROGRESS_UPDATED,
                    {'progress_type': 'input', 'input_id': input_id, 'percent_engrams_complete': 0.0},
                )

        # else: lesson may have already created the entries.

    def on_engram_created(self, msg: dict[Any, Any]) -> None:
        input_id = msg['input_id']
        engram_id_array = msg['engram_id_array']

        if input_id in self.progress_items:
            input_process = self.progress_items[input_id]
            for engram_id in engram_id_array:
                input_process.engram_list[engram_id] = False

    def on_index_created(self, msg: dict[Any, Any]) -> None:
        input_id = msg['input_id']
        index_id_array = msg['index_id_array']

        if input_id in self.progress_items:
            input_process = self.progress_items[input_id]
            for index_id in index_id_array:
                input_process.index_list[index_id] = False

    def _on_index_inserted(self, msg: dict[Any, Any]) -> None:
        input_id = msg['input_id']
        index_id_array = msg['index_id_array']
        engram_id = msg['engram_id']

        if input_id in self.progress_items:
            input_process = self.progress_items[input_id]

            for index_id in index_id_array:
                input_process.index_list[index_id] = True

            input_process.engram_list[engram_id] = True

            total_engram = len(input_process.engram_list)
            sum_engrams = sum(input_process.engram_list.values())

            lesson_id = self.progress_items[input_id].lesson_id

            if not lesson_id:
                self.send_message_async(
                    Service.Topic.PROGRESS_UPDATED,
                    {
                        'progress_type': 'input',
                        'input_id': input_id,
                        'percent_engrams_complete': sum_engrams / total_engram,
                    },
                )

            if all(input_process.engram_list.values()):
                self.progress_items[input_id].completed = True
                self.send_message_async(Service.Topic.INPUT_COMPLETED, {'input_id': input_id})

                if lesson_id:
                    input_array = self.lesson_items[lesson_id]

                    lesson_inputs = [self.progress_items[input_id].completed for input_id in input_array]

                    total_inputs = len(lesson_inputs)
                    sum_inputs = sum(lesson_inputs)

                    self.send_message_async(
                        Service.Topic.PROGRESS_UPDATED,
                        {
                            'progress_type': 'lesson',
                            'lesson_id': lesson_id,
                            'percent_inputs_complete': sum_inputs / total_inputs,
                        },
                    )

                    if all(lesson_inputs):
                        self.send_message_async(Service.Topic.LESSON_COMPLETED, {'lesson_id': lesson_id})
                        del self.lesson_items[lesson_id]

                else:
                    del self.progress_items[input_id]

        else:
            logging.error('on_index_inserted call made with input not in progress items. Item removed prematurely?')

    def on_lesson_created(self, msg: dict[Any, Any]) -> None:
        lesson_id = msg['lesson_id']
        input_id_array = msg['input_array']

        self.lesson_items[lesson_id] = input_id_array

        for input_id in input_id_array:
            self.on_input_create({'input_id': input_id, 'type': 'prompt'}, lesson_id)
