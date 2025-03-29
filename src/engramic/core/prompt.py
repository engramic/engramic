# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Prompt:
    prompt_str: str | None = None
    input_data: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.input_data.update({'prompt_str': self.prompt_str})

    def render_prompt(self) -> str:
        return self.prompt_str or ''
