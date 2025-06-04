# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.
from __future__ import annotations

import hashlib
import os
import sys
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


@dataclass
class Document:
    class Root(Enum):
        RESOURCE = 'resource'
        DATA = 'data'

    root_directory: str
    file_path: str
    file_name: str
    id: str = ''
    repo_id: str | None = None
    tracking_id: str | None = None
    is_scanned: bool = False

    def get_source_id(self) -> str:
        full_path = self.file_path + '/' + self.file_name
        return hashlib.md5(str(full_path).encode('utf-8')).hexdigest()

    def __post_init__(self) -> None:
        if self.root_directory == self.Root.RESOURCE.value:
            # Treat as dotted module path + file name
            self.file_path = self.file_path.rstrip('.\\/')
            self.file_name = self.file_name.lstrip('.\\/')
        elif self.root_directory == self.Root.DATA.value:
            # Use cross-platform local data path
            self.file_name = self.file_name.strip('/\\')
        else:
            error = f'Unknown root directory: {self.root_directory}'
            raise ValueError(error)

        self.id = self.get_source_id()

        if self.tracking_id is None:
            self.tracking_id = str(uuid.uuid4())

    @staticmethod
    def get_data_root(app_name: str = 'engramic') -> str:
        if sys.platform == 'win32':
            # Example: C:\Users\Username\AppData\Local\Engramic
            base = os.getenv('LOCALAPPDATA', Path.home() / 'AppData' / 'Local')
        elif sys.platform == 'darwin':
            # Example: /Users/username/Library/Application Support/Engramic
            base = Path.home() / 'Library' / 'Application Support'
        else:
            # Example: /home/username/.local/share/Engramic
            base = Path.home() / '.local' / 'share'
        return str(base) + '/' + app_name
