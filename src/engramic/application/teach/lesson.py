# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

"""
Implements the Lesson class for generating educational content from documents.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import TYPE_CHECKING, Any

from engramic.application.teach.prompt_gen_questions import PromptGenQuestions
from engramic.infrastructure.system.service import Service

if TYPE_CHECKING:
    from concurrent.futures import Future

    from engramic.application.teach.teach_service import TeachService
    from engramic.core.meta import Meta


class Lesson:
    """
    Represents an educational lesson generated from a document.

    Handles the generation of questions and educational prompts based on
    document content and metadata.

    Attributes:
        id (str): Unique identifier for the lesson.
        doc_id (str): Identifier of the source document.
        tracking_id (str): ID for tracking the lesson's progress.
        service (TeachService): Parent service managing this lesson.
        meta (Meta): Metadata about the source document.

    Methods:
        run_lesson(meta_in) -> None:
            Initiates the lesson generation process.
        generate_questions() -> Any:
            Generates educational questions based on document content.
        on_questions_generated(future) -> None:
            Processes generated questions and creates prompts.
        _on_send_prompt_complete(ret) -> None:
            Handles completion of prompt submission.
    """

    def __init__(self, parent_service: TeachService, lesson_id: str, tracking_id: str, doc_id: str) -> None:
        """
        Initializes a new Lesson instance.

        Args:
            parent_service (TeachService): The service managing this lesson.
            lesson_id (str): Unique identifier for the lesson.
            tracking_id (str): ID for tracking the lesson's progress.
            doc_id (str): Identifier of the source document.
        """
        self.id = lesson_id
        self.doc_id = doc_id
        self.tracking_id = tracking_id
        self.service = parent_service

    def run_lesson(self, meta_in: Meta) -> None:
        """
        Initiates the lesson generation process.

        Stores the document metadata and starts the question generation task.

        Args:
            meta_in (Meta): Metadata about the source document.
        """
        self.meta = meta_in
        future = self.service.run_task(self.generate_questions())
        future.add_done_callback(self.on_questions_generated)

    async def generate_questions(self) -> Any:
        """
        Generates educational questions based on document content.

        Uses an LLM plugin to generate study questions from the document metadata.

        Returns:
            dict: The generated questions and study actions.
        """
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
        """
        Processes generated questions and creates learning prompts.

        Takes the questions from the generator and submits them as learning prompts.
        Also adds document-specific questions and notifies about lesson creation.

        Args:
            future (Future[Any]): Future containing the generated questions.
        """
        res = future.result()
        text_prompts = res['study_actions']

        if self.meta.type == self.meta.SourceType.DOCUMENT.value:
            location = self.meta.locations[0]

            # generate some static question for file discovery.
            text_prompts.append(f'Tell me about the file {location}')

        async def send_prompt(question: str) -> None:
            self.service.send_message_async(
                Service.Topic.SUBMIT_PROMPT,
                {
                    'prompt_str': question,
                    'parent_id': self.id,
                    'training_mode': True,
                    'is_lesson': True,
                    'tracking_id': self.tracking_id,
                    'repo_ids_filters': self.meta.repo_ids,
                },
            )

        for text_prompt in reversed(text_prompts):
            future = self.service.run_task(send_prompt(text_prompt))
            future.add_done_callback(self._on_send_prompt_complete)

        async def send_lesson() -> None:
            self.service.send_message_async(
                Service.Topic.LESSON_CREATED,
                {'id': self.id, 'tracking_id': self.tracking_id, 'doc_id': self.doc_id},
            )

        self.service.run_task(send_lesson())

    def _on_send_prompt_complete(self, ret: Future[Any]) -> None:
        """
        Handles completion of prompt submission.

        Args:
            ret (Future[Any]): Future representing the completed prompt submission.
        """
        ret.result()
