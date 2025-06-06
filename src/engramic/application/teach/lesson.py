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
    def __init__(self, parent_service: TeachService, source_id: str, lesson_id: str) -> None:
        self.id = lesson_id
        self.source_id = source_id
        self.service = parent_service

    def run_lesson(self, meta_in: Meta) -> None:
        self.meta = meta_in
        future = self.service.run_task(self.generate_questions())
        future.add_done_callback(self.on_questions_generated)

    async def generate_questions(self) -> Any:
        plugin = self.service.teach_generate_questions

        prompt = PromptGenQuestions(input_data={'meta': asdict(self.meta)})

        structured_response = {'study_actions': list[str]}

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
        questions = res['study_actions']

        async def send_prompt(question: str, source_id: str) -> None:
            self.service.send_message_async(
                Service.Topic.SUBMIT_PROMPT,
                {'prompt_str': question, 'source_id': source_id, 'training_mode': True, 'is_lesson': True},
            )

        # print(questions)
        source_array = []
        for question in reversed(questions):
            source_id = str(uuid.uuid4())
            source_array.append(source_id)
            self.service.run_task(send_prompt(question, source_id))

        async def send_lesson() -> None:
            self.service.send_message_async(
                Service.Topic.LESSON_CREATED,
                {'source_id': self.source_id, 'lesson_id': self.id, 'source_array': source_array},
            )

        self.service.run_task(send_lesson())
