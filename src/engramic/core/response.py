# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engramic.core import PromptAnalysis
    from engramic.core.retrieve_result import RetrieveResult


@dataclass
class Response:
    id: str
    response: str
    retrieve_result: RetrieveResult
    prompt_str: str
    analysis: PromptAnalysis
    model: str
    response_time: float | None = None
    hash: str | None = None

    def __post_init__(self) -> None:
        if self.hash is None:
            self.hash = hashlib.md5(self.response.encode('utf-8')).hexdigest()  # nosec

        if self.response_time is None:
            self.response_time = datetime.now(timezone.utc).timestamp()
