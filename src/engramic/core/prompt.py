# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Prompt:
    prompt_str: str = ''
    prompt_id: str = ''
    repo_ids_filters: list[str] | None = None
    training_mode: bool | None = False
    is_lesson: bool | None = False
    input_data: dict[str, Any] = field(default_factory=dict)
    parent_id: str | None = None
    tracking_id: str | None = None

    def __post_init__(self) -> None:
        if not self.prompt_id:
            self.prompt_id = str(uuid.uuid4())

        if self.repo_ids_filters == []:
            error = 'Empty set [] is not allowed on Prompts for repo_ids_filters, set to None to indicate no repos are in use. If you want all filters, you must name them explicitly.'
            raise RuntimeError(error)

        self.input_data.update({
            'prompt_str': self.prompt_str,
            'training_mode': self.training_mode,
            'is_lesson': self.is_lesson,
            'repo_ids_filters': self.repo_ids_filters,
        })  # include the prompt_str as input_data to be used in mako rendering.

        if self.tracking_id is None:
            self.tracking_id = str(uuid.uuid4())

    def render_prompt(self) -> str:
        return self.prompt_str or ''
