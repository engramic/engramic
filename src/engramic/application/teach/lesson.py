# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from typing import TYPE_CHECKING, Any

from engramic.application.teach.prompt_gen_questions import PromptGenQuestions
from engramic.infrastructure.system.service import Service

if TYPE_CHECKING:
    from concurrent.futures import Future

    from engramic.application.teach.teach_service import TeachService
    from engramic.core.meta import Meta


class Lesson:
    def __init__(self, parent_service: TeachService, lesson_id: str) -> None:
        self.id = lesson_id
        self.service = parent_service

    def run_lesson(self, meta_in: Meta) -> None:
        self.meta = meta_in
        future = self.service.run_task(self.generate_questions())
        future.add_done_callback(self.on_questions_generated)

    async def generate_questions(self) -> Any:
        plugin = self.service.teach_generate_questions

        prompt = PromptGenQuestions(input_data={'meta': asdict(self.meta)})

        structured_response = {'questions': list[str]}

        ret = plugin['func'].submit(
            prompt=prompt,
            images=None,
            structured_schema=structured_response,
            args=self.service.host.mock_update_args(plugin),
        )

        self.service.host.update_mock_data(plugin, ret)

        initial_scan = json.loads(ret[0]['llm_response'])

        return initial_scan

    def on_questions_generated(self, future: Future[Any]) -> None:
        res = future.result()
        questions = res['questions']

        async def send_prompt(question: str, input_id: str) -> None:
            self.service.send_message_async(
                Service.Topic.SUBMIT_PROMPT, {'prompt_str': question, 'input_id': input_id, 'training_mode': True}
            )

        input_array = []
        for question in questions:
            input_id = str(uuid.uuid4())
            input_array.append(input_id)
            self.service.run_task(send_prompt(question, input_id))

        async def send_lesson() -> None:
            self.service.send_message_async(
                Service.Topic.LESSON_CREATED, {'lesson_id': str(uuid.uuid4()), 'input_array': input_array}
            )

        self.service.run_task(send_lesson())
