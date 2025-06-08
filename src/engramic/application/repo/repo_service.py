# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.
from __future__ import annotations

import json
import logging
import os
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING, Any

import tomli

from engramic.core.document import Document
from engramic.infrastructure.repository.document_repository import DocumentRepository
from engramic.infrastructure.system.service import Service

if TYPE_CHECKING:
    from concurrent.futures import Future

    from engramic.core.host import Host
    from engramic.infrastructure.system.plugin_manager import PluginManager


class RepoService(Service):
    def __init__(self, host: Host) -> None:
        super().__init__(host)
        self.plugin_manager: PluginManager = host.plugin_manager
        self.db_document_plugin = self.plugin_manager.get_plugin('db', 'document')
        self.document_repository: DocumentRepository = DocumentRepository(self.db_document_plugin)
        self.repos: dict[str, str] = {}  # memory copy of all folders
        self.file_index: dict[str, Any] = {}  # memory copy of all files
        self.file_repos: dict[str, Any] = {}  # memory copy of all files in repos
        self.submitted_documents: set[str] = set()

    def start(self) -> None:
        self.subscribe(Service.Topic.REPO_SUBMIT_IDS, self._on_submit_ids)
        self.subscribe(Service.Topic.DOCUMENT_COMPLETE, self.on_document_complete)
        super().start()

    def init_async(self) -> None:
        return super().init_async()

    def _on_submit_ids(self, msg: str) -> None:
        json_msg = json.loads(msg)
        id_array = json_msg['submit_ids']
        self.submit_ids(id_array)

    def submit_ids(self, id_array: list[str]) -> None:
        for sub_id in id_array:
            document = self.file_index[sub_id]
            self.send_message_async(
                Service.Topic.SUBMIT_DOCUMENT,
                asdict(document),
            )
            self.submitted_documents.add(document.id)

    def on_document_complete(self, msg: dict[str, Any]) -> None:
        document_id = msg['id']
        document = Document(**msg)

        if document_id in self.submitted_documents:
            self.submitted_documents.remove(document_id)

            document.is_scanned = True  # Create a Document instance to validate the data
            self.document_repository.save(document)

        if document.repo_id:
            self.run_task(self.update_repo_files(document.repo_id, [document_id]))

    def _load_repository_id(self, folder_path: Path) -> str:
        repo_file = folder_path / '.repo'
        if not repo_file.is_file():
            error = f"Repository config file '.repo' not found in folder '{folder_path}'."
            raise RuntimeError(error)
        with repo_file.open('rb') as f:
            data = tomli.load(f)
        try:
            repository_id = data['repository']['id']
        except KeyError as err:
            error = f"Missing 'repository.id' entry in .repo file at '{repo_file}'."
            raise RuntimeError(error) from err
        if not isinstance(repository_id, str):
            error = f"'repository.id' must be a string in '{repo_file}'."
            raise TypeError
        return repository_id

    def _discover_repos(self, repo_root: Path) -> None:
        for name in os.listdir(repo_root):
            folder_path = repo_root / name
            if folder_path.is_dir():
                if name == 'null':
                    error = "Folder name 'null' is reserved and cannot be used as a repository name."
                    logging.error(error)
                    raise ValueError(error)
                try:
                    repo_id = self._load_repository_id(folder_path)
                    self.repos[repo_id] = name
                except (FileNotFoundError, PermissionError, ValueError, OSError) as e:
                    info = f"Skipping '{name}': {e}"
                    logging.info(info)

    async def update_repo_files(self, repo_id: str, update_ids: list[str] | None = None) -> None:
        document_dicts = []

        folder = self.repos[repo_id]

        update_list = self.file_repos[repo_id] if update_ids is None else update_ids

        document_dicts = [asdict(self.file_index[document_id]) for document_id in update_list]

        self.send_message_async(
            Service.Topic.REPO_FILES,
            {'repo': folder, 'repo_id': repo_id, 'files': document_dicts},
        )

    def scan_folders(self) -> None:
        repo_root = os.getenv('REPO_ROOT')
        if repo_root is None:
            error = "Environment variable 'REPO_ROOT' is not set."
            raise RuntimeError(error)

        expanded_repo_root = Path(repo_root).expanduser()

        self._discover_repos(expanded_repo_root)

        async def send_message() -> None:
            self.send_message_async(Service.Topic.REPO_FOLDERS, {'repo_folders': self.repos})

        self.run_task(send_message())

        for repo_id in self.repos:
            folder = self.repos[repo_id]
            document_ids = []
            # Recursively walk through all files in repo
            for root, dirs, files in os.walk(expanded_repo_root / folder):
                del dirs
                for file in files:
                    if file.startswith('.'):
                        continue  # Skip hidden files
                    file_path = Path(root) / file
                    relative_path = file_path.relative_to(expanded_repo_root / folder)
                    relative_dir = str(relative_path.parent) if relative_path.parent != Path('.') else ''
                    doc = Document(
                        root_directory=Document.Root.DATA.value,
                        file_path=folder + relative_dir,
                        file_name=file,
                        repo_id=repo_id,
                        tracking_id=str(uuid.uuid4()),
                    )

                    fetched_doc: dict[str, Any] = self.document_repository.load(doc.id)
                    if len(fetched_doc['document']) == 0:
                        document_ids.append(doc.id)
                    else:
                        doc = Document(**fetched_doc['document'][0])
                        document_ids.append(doc.id)

                    self.file_index[doc.id] = doc

            self.file_repos[repo_id] = document_ids
            future = self.run_task(self.update_repo_files(repo_id))
            future.add_done_callback(self._on_update_repo_files_complete)

    def _on_update_repo_files_complete(self, ret: Future[Any]) -> None:
        ret.result()
