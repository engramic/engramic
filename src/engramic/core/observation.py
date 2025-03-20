# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from dataclasses import dataclass

from engramic.core.engram import Engram
from engramic.core.meta import Meta


@dataclass
class Observation:
    id: str
    meta: Meta
    engram: list[Engram]
