# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


@dataclass
class Prompt:
    class Retrievaltype(Enum):
        ASK = 'ask'
        FETCH = 'fetch'

    prompt_str: str = ''
    prompt_id: str = ''
    is_background: bool = False
    repo_ids_filters: list[str] | None = field(default_factory=list)
    training_mode: bool | None = False
    is_lesson: bool | None = False
    is_on_demand: bool | None = False
    include_default_repos: bool | None = False
    widget_cmd: str | None = None
    server_side_cmd: str | None = None
    retrieval_type: str | None = None
    save_in_history: bool | None = True
    input_data: dict[str, Any] = field(default_factory=dict)
    conversation_id: str | None = None
    parent_id: str | None = None
    tracking_id: str | None = None
    thinking_level: float | None = None
    target_single_file: bool | None = None

    def __post_init__(self) -> None:
        if not self.prompt_id:
            self.prompt_id = str(uuid.uuid4())

        # if self.repo_ids_filters == []:
        #    error = 'Empty set [] is not allowed on Prompts for repo_ids_filters, set to None to indicate no repos are in use. If you want all filters, you must name them explicitly.'
        #    raise RuntimeError(error)

        # Remove all widget commands from prompt_str
        self.input_data['prompt_str'] = self.prompt_str

        self.input_data.update({
            'prompt_str': self.prompt_str,
            'training_mode': self.training_mode,
            'is_lesson': self.is_lesson,
            'is_on_demand': self.is_on_demand,
            'repo_ids_filters': self.repo_ids_filters,
        })  # include the prompt_str as input_data to be used in mako rendering.

        if self.tracking_id is None:
            self.tracking_id = str(uuid.uuid4())

    def render_prompt(self) -> str:
        return self.prompt_str or ''
