# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.
from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass()
class Index:
    text: str
    embedding: list[float] | None = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
