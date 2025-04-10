# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engramic.core import Engram, Meta


@dataclass()
class Observation(ABC):
    id: str
    meta: Meta
    engram_list: list[Engram]
    created_date: float | None = None
