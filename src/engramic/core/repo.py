# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Repo:
    name: str = ''
    repo_id: str = ''
    is_default: bool = False
