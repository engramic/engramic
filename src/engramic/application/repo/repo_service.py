# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import copy
import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

from engramic.core.document import Document
from engramic.core.host import Host
from engramic.infrastructure.system.service import Service


class RepoService(Service):
    def __init__(self, host: Host) -> None:
        super().__init__(host)
        self.repo_roots: list[str] = []
        self.file_index: dict[str, Any] = {}

    def start(self) -> None:
        self.subscribe(Service.Topic.REPO_SUBMIT_IDS, self._on_submit_ids)
        super().start()

    def init_async(self) -> None:
        return super().init_async()

    def _on_submit_ids(self, msg: str) -> None:
        json_msg = json.loads(msg)
        id_array = json_msg['submit_ids']

        for sub_id in id_array:
            file = self.file_index[sub_id]
            self.send_message_async(
                Service.Topic.SUBMIT_DOCUMENT,
                {
                    'file_path': file['file_path'],
                    'file_name': file['file_name'],
                    'root_directory': Document.Root.DATA.value,
                },
            )

    def scan_folders(self) -> None:
        repo_root = os.getenv('REPO_ROOT')
        if repo_root is None:
            error = "Environment variable 'REPO_ROOT' is not set."
            raise RuntimeError(error)

        expanded_repo_root = Path(repo_root).expanduser()

        folder_names = [
            name for name in os.listdir(expanded_repo_root) if os.path.isdir(os.path.join(expanded_repo_root, name))
        ]

        self.repo_roots = folder_names

        async def send_message() -> None:
            self.send_message_async(Service.Topic.REPO_FOLDERS, {'repo_folders': self.repo_roots})

        self.run_task(send_message())

        for folder in self.repo_roots:
            documents = []
            # Recursively walk through all files in repo
            for root, dirs, files in os.walk(expanded_repo_root / folder):
                del dirs
                for file in files:
                    file_path = Path(root) / file
                    relative_path = file_path.relative_to(expanded_repo_root / folder)
                    relative_dir = str(relative_path.parent) if relative_path.parent != Path('.') else ''

                    doc = asdict(
                        Document(root_directory=Document.Root.DATA, file_path=folder + relative_dir, file_name=file)
                    )
                    doc.pop('root_directory', None)  # Remove if unnecessary in your payload
                    self.file_index[doc['id']] = doc
                    documents.append(doc)

            async def send_message_files(folder: str, documents: list[dict[str, Any]]) -> None:
                self.send_message_async(Service.Topic.REPO_FILES, {'folder': folder, 'files': documents})

            self.run_task(send_message_files(folder, copy.deepcopy(documents)))
