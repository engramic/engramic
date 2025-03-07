# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, list

if TYPE_CHECKING:
    from context import Context


@dataclass()
class Meta:
    """
    Test.
    """

    def __init__(
        self,
        location: str,
        source_id: str,
        keywords: list[str],
        summary_initial: str | None = None,
        summary_full: str | None = None,
        context: Context | None = None,
    ):
        self.id = str(uuid.uuid4())
        self.location = location
        self.source_id = source_id
        self.keywords = keywords
        self.summary = summary_initial
        self.summary = summary_full
        self.context = context
