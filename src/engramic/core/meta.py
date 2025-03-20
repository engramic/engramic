# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from __future__ import annotations

from dataclasses import dataclass


@dataclass()
class Meta:
    """
    Test.
    """

    id: str
    locations: str
    source_ids: list[str]
    keywords: list[str]
    summary_initial: str | None = None
    summary_full: str | None = None
