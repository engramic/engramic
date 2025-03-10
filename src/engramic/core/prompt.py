# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import uuid
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Prompt:
    id: str = field(default_factory=lambda: str(uuid.uuid4()), init=False)
    user_input: str

