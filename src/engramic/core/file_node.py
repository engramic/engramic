# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.
from __future__ import annotations

import hashlib
import os
import sys
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


@dataclass
class FileNode:
    class Root(Enum):
        RESOURCE = 'resource'
        DATA = 'data'

    class Type(Enum):
        FILE = 'file'
        FOLDER = 'folder'

    root_directory: str

    file_name: str
    node_type: str = Type.FILE.value  # Add node_type field
    file_dirs: list[str] = field(default_factory=list)

    id: str = ''
    module_path: str | None = None
    repo_id: str | None = None
    tracking_id: str | None = None
    percent_complete_document: float | None = 0.0
    percent_complete_lesson: float | None = 0.0

    def get_source_id(self) -> str:
        if self.root_directory == self.Root.RESOURCE.value:
            full_path = self.module_path
        elif self.root_directory == self.Root.DATA.value:
            path = os.path.join(*self.file_dirs)
            full_path = path + '/' + self.file_name

        # Include node_type in the hash to distinguish between files and folders with same path
        hash_input = f'{full_path}:{self.node_type}'
        hash_val = hashlib.md5(hash_input.encode('utf-8')).hexdigest()
        return hash_val

    def __post_init__(self) -> None:
        if self.root_directory == self.Root.RESOURCE.value:
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

    @property
    def file_path(self) -> str:
        """Assemble the full path from file_dirs components."""
        if not self.file_dirs:
            return ''
        return '/'.join(self.file_dirs)

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
