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
    training_mode: bool | None = False
    is_lesson: bool | None = False
    input_data: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.prompt_id:
            self.prompt_id = str(uuid.uuid4())

        self.input_data.update({
            'prompt_str': self.prompt_str,
            'training_mode': self.training_mode,
            'is_lesson': self.is_lesson,
        })  # include the prompt_str as input_data to be used in mako rendering.

    def render_prompt(self) -> str:
        return self.prompt_str or ''
