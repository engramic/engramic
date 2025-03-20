# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from dataclasses import dataclass


@dataclass
class RetrieveResult:
    engram_id_array: list[str]
