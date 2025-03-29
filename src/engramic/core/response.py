# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engramic.core import Prompt, PromptAnalysis
    from engramic.core.retrieve_result import RetrieveResult


@dataclass
class Response:
    id: str
    response: str
    retrieve_result: RetrieveResult
    prompt: Prompt
    analysis: PromptAnalysis
    model: str
    hash: str | None = None

    def __post_init__(self) -> None:
        if self.hash is None:
            self.hash = hashlib.md5(self.response.encode('utf-8')).hexdigest()  # nosec
