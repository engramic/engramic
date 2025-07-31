# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


@dataclass
class Process:
    class Status(Enum):
        INIT = 'init'
        PREP = 'prep'
        RUNNING = 'running'
        DONE = 'done'

    process_name: str
    id: str
    percent_complete: float
    document_id: str | None = None
    start_time: int = field(default_factory=lambda: int(time.time()))
    status: str = Status.INIT.value
