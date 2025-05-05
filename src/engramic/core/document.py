# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.
from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass
class Document:
    is_resource: bool
    resource_path: str
    file_name: str
    id: str = ''

    def get_source_id(self) -> str:
        full_path = self.resource_path + '/' + self.file_name
        return hashlib.md5(full_path.encode('utf-8')).hexdigest()

    def __post_init__(self) -> None:
        self.id = self.get_source_id()
