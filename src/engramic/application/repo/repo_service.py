# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.
"""
Provides repository management services for the Engramic system.

This module handles repository discovery, document tracking, and file indexing
for projects managed by Engramic.
"""

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
from engramic.core.repo import Repo  # Add this import
from engramic.infrastructure.repository.document_repository import DocumentRepository
from engramic.infrastructure.repository.engram_repository import EngramRepository
from engramic.infrastructure.repository.observation_repository import ObservationRepository
from engramic.infrastructure.system.service import Service

if TYPE_CHECKING:
    from concurrent.futures import Future

    from engramic.core.host import Host
    from engramic.core.observation import Observation
    from engramic.infrastructure.system.plugin_manager import PluginManager


class RepoService(Service):
    """
    Service for managing repositories and their document contents.

    Handles repository discovery, file indexing, and document submission for processing.
    Maintains in-memory indices of repositories and their files. Supports loading of .engram
    files and processing of PDF documents.

    Attributes:
        plugin_manager (PluginManager): Manager for system plugins.
        db_document_plugin (Any): Plugin for document database operations.
        document_repository (DocumentRepository): Repository for document storage and retrieval.
        engram_repository (EngramRepository): Repository for engram storage and retrieval.
        observation_repository (ObservationRepository): Repository for observation storage and retrieval.
        repos (dict[str, Repo]): Mapping of repository IDs to Repo objects.
        file_index (dict[str, Any]): Index of all files by document ID.
        file_repos (dict[str, Any]): Mapping of repository IDs to lists of document IDs.
        submitted_documents (set[str]): Set of document IDs that have been submitted for processing.

    Methods:
        start() -> None:
            Starts the service and subscribes to relevant topics.
        init_async() -> None:
            Initializes asynchronous components of the service.
        submit_ids(id_array, overwrite) -> None:
            Submits documents for processing by their IDs.
        scan_folders(repo_id) -> None:
            Discovers repositories and indexes their files.
        update_repo_files(repo_id, update_ids) -> None:
            Updates the list of files for a repository.
    """

    def __init__(self, host: Host) -> None:
        """
        Initializes the repository service.

        Args:
            host (Host): The host system that this service is attached to.
        """
        super().__init__(host)
        self.plugin_manager: PluginManager = host.plugin_manager
        self.db_document_plugin = self.plugin_manager.get_plugin('db', 'document')
        self.document_repository: DocumentRepository = DocumentRepository(self.db_document_plugin)
        self.engram_repository: EngramRepository = EngramRepository(self.db_document_plugin)
        self.observation_repository: ObservationRepository = ObservationRepository(self.db_document_plugin)
        self.repos: dict[str, Repo] = {}  # memory copy of all folders
        self.file_index: dict[str, Any] = {}  # memory copy of all files
        self.file_repos: dict[str, Any] = {}  # memory copy of all files in repos
        self.submitted_documents: set[str] = set()

    def start(self) -> None:
        """
        Starts the repository service and subscribes to relevant topics.
        """
        self.subscribe(Service.Topic.REPO_SUBMIT_IDS, self._on_submit_ids)
        self.subscribe(Service.Topic.REPO_UPDATE_REPOS, self.scan_folders)
        self.subscribe(Service.Topic.PROGRESS_UPDATED, self._on_progress_updated)
        super().start()
        self.scan_folders()

    def init_async(self) -> None:
        """
        Initializes asynchronous components of the service.
        """
        return super().init_async()

    def _on_submit_ids(self, msg: str) -> None:
        """
        Handles the REPO_SUBMIT_IDS message.

        Args:
            msg (str): JSON message containing document IDs to submit.
        """
        json_msg = json.loads(msg)
        id_array = json_msg['submit_ids']
        overwrite = False
        if 'overwrite' in json_msg:
            overwrite = json_msg['overwrite']
        self.submit_ids(id_array, overwrite=overwrite)

    def submit_ids(self, id_array: list[str], *, overwrite: bool = False) -> None:
        """
        Submits documents for processing by their IDs.

        Args:
            id_array (list[str]): List of document IDs to submit.
            overwrite (bool): Whether to overwrite existing documents. Defaults to False.
        """
        for sub_id in id_array:
            document = self.file_index[sub_id]
            self.send_message_async(
                Service.Topic.SUBMIT_DOCUMENT, {'document': asdict(document), 'overwrite': overwrite}
            )
            self.submitted_documents.add(document.id)

    def _load_repository(self, folder_path: Path) -> tuple[str, bool]:
        """
        Loads the repository ID from a .repo file.

        Args:
            folder_path (Path): Path to the repository folder.

        Returns:
            str: The repository ID.

        Raises:
            RuntimeError: If the .repo file is missing or invalid.
            TypeError: If the repository ID is not a string.
        """
        repo_file = folder_path / '.repo'
        if not repo_file.is_file():
            error = f"Repository config file '.repo' not found in folder '{folder_path}'."
            raise RuntimeError(error)
        with repo_file.open('rb') as f:
            data = tomli.load(f)
        try:
            repository_id = data['repository']['id']
            is_default = False
            if 'is_default' in data['repository']:
                is_default = data['repository']['is_default']

        except KeyError as err:
            error = f"Missing 'repository.id' entry in .repo file at '{repo_file}'."
            raise RuntimeError(error) from err
        if not isinstance(repository_id, str):
            error = "'repository.id' must be a string in '%s'."
            raise TypeError(error % repo_file)
        return repository_id, is_default

    def _discover_repos(self, repo_root: Path) -> None:
        """
        Discovers repositories in the specified root directory.

        Args:
            repo_root (Path): Root directory containing repositories.

        Raises:
            ValueError: If a repository is named 'null'.
        """
        for name in os.listdir(repo_root):
            folder_path = repo_root / name
            if folder_path.is_dir():
                if name == 'null':
                    error = "Folder name 'null' is reserved and cannot be used as a repository name."
                    logging.error(error)
                    raise ValueError(error)
                try:
                    repo_id, is_default = self._load_repository(folder_path)
                    self.repos[repo_id] = Repo(name=name, repo_id=repo_id, is_default=is_default)
                except (FileNotFoundError, PermissionError, ValueError, OSError) as e:
                    info = "Skipping '%s': %s"
                    logging.info(info, name, e)

    def _on_progress_updated(self, msg: dict[str, Any]) -> None:
        progress_type = msg['progress_type']
        doc_id = None
        if progress_type == 'document':
            doc_id = msg['id']
        if progress_type == 'lesson':
            doc_id = msg['target_id']

        if doc_id is not None and doc_id in self.file_index:  # might be a different progress update
            file = self.file_index[doc_id]

            if progress_type == 'document':
                file.percent_complete_document = msg['percent_complete']
            elif progress_type == 'lesson':
                file.percent_complete_lesson = msg['percent_complete']

            folder = self.repos[file.repo_id].name

            self.send_message_async(
                Service.Topic.REPO_FILES,
                {'repo': folder, 'repo_id': file.repo_id, 'files': [asdict(file)]},
            )

    async def update_repo_files(self, repo_id: str, update_ids: list[str] | None = None) -> None:
        """
        Updates the list of files for a repository.

        Args:
            repo_id (str): ID of the repository to update.
            update_ids (list[str] | None): List of document IDs to update. If None, updates all files.
        """
        document_dicts = []

        folder = self.repos[repo_id].name

        update_list = self.file_repos[repo_id] if update_ids is None else update_ids

        document_dicts = [asdict(self.file_index[document_id]) for document_id in update_list]

        self.send_message_async(
            Service.Topic.REPO_FILES,
            {'repo': folder, 'repo_id': repo_id, 'files': document_dicts},
        )

    def scan_folders(self, repo_id: dict[str, str] | None = None) -> None:
        """
        Scans repository folders and indexes their files.

        Discovers repositories, indexes their files, and sends messages with the repository information.

        Args:
            repo_id (dict[str,str] | None): Optional dictionary containing repository ID with key "repo_id". If None, scans all repositories.

        Raises:
            RuntimeError: If the REPO_ROOT environment variable is not set.
            ValueError: If the specified repo_id is not found.
        """
        repo_root = self._get_repo_root()
        repos_to_scan = self._determine_repos_to_scan(repo_id, repo_root)

        self._send_repo_folders_message()
        self._scan_and_index_repos(repos_to_scan, repo_root)

    def _get_repo_root(self) -> Path:
        """Get and validate the repository root path."""
        repo_root = os.getenv('REPO_ROOT')
        if repo_root is None:
            error = "Environment variable 'REPO_ROOT' is not set."
            raise RuntimeError(error)
        return Path(repo_root).expanduser()

    def _determine_repos_to_scan(self, repo_id: dict[str, str] | None, repo_root: Path) -> dict[str, Repo]:
        """Determine which repositories need to be scanned."""
        target_repo_id = repo_id.get('repo_id') if repo_id is not None else None

        if target_repo_id is not None:
            return self._get_specific_repo(target_repo_id, repo_root)
        self._discover_repos(repo_root)
        return self.repos

    def _get_specific_repo(self, target_repo_id: str, repo_root: Path) -> dict[str, Repo]:
        """Get a specific repository, discovering it if necessary."""
        if target_repo_id not in self.repos:
            self._discover_repos(repo_root)
            if target_repo_id not in self.repos:
                error = f"Repository with ID '{target_repo_id}' not found."
                raise ValueError(error)
        return {target_repo_id: self.repos[target_repo_id]}

    def _send_repo_folders_message(self) -> None:
        """Send async message with repository folders."""

        async def send_message() -> None:
            # Convert Repo objects to dictionaries for serialization
            repos_dict = {repo_id: asdict(repo) for repo_id, repo in self.repos.items()}
            self.send_message_async(Service.Topic.REPO_FOLDERS, {'repo_folders': repos_dict})

        self.run_task(send_message())

    def _scan_and_index_repos(self, repos_to_scan: dict[str, Repo], repo_root: Path) -> None:
        """Scan and index files in the specified repositories."""
        for current_repo_id, repo in repos_to_scan.items():
            document_ids = self._index_repo_files(current_repo_id, repo.name, repo_root)
            self.file_repos[current_repo_id] = document_ids
            future = self.run_task(self.update_repo_files(current_repo_id))
            future.add_done_callback(self._on_update_repo_files_complete)

    def _index_repo_files(self, repo_id: str, folder: str, repo_root: Path) -> list[str]:
        """Index all files in a repository folder."""
        document_ids = []
        for root, dirs, files in os.walk(repo_root / folder):
            del dirs
            for file in files:
                if file.startswith('.'):
                    continue  # Skip hidden files

                doc = self._handle_file_by_type(repo_id, folder, root, file, repo_root)
                if doc is not None:
                    document_ids.append(doc.id)
                    self.file_index[doc.id] = doc

        return document_ids

    def _handle_file_by_type(self, repo_id: str, folder: str, root: str, file: str, repo_root: Path) -> Document | None:
        """Handle different file types and return a Document if applicable."""
        file_path = Path(root) / file
        relative_path = file_path.relative_to(repo_root / folder)
        relative_dir = str(relative_path.parent) if relative_path.parent != Path('.') else ''

        # Handle different file types
        file_extension = Path(file).suffix.lower()

        if file_extension == '.pdf':
            return self._create_document_from_pdf(repo_id, folder, relative_dir, file)
        if file_extension == '.engram':
            self._load_engram_file(file_path)
            return None
        # Skip other file types
        return None

    def _create_document_from_pdf(self, repo_id: str, folder: str, relative_dir: str, file_name: str) -> Document:
        """Create a Document object for PDF files."""
        doc = Document(
            root_directory=Document.Root.DATA.value,
            file_path=folder + relative_dir,
            file_name=file_name,
            repo_id=repo_id,
            tracking_id=str(uuid.uuid4()),
        )

        # Check to see if the document has been loaded before.
        fetched_doc: dict[str, Any] = self.document_repository.load(doc.id)

        # If it has been loaded, add that one to the file_index.
        if len(fetched_doc['document']) != 0:
            doc = Document(**fetched_doc['document'][0])

        return doc

    def _load_engram_file(self, file_path: Path) -> None:
        """
        Load an .engram TOML file.

        Args:
            repo_id (str): Repository ID
            folder (str): Repository folder name
            relative_dir (str): Relative directory path
            file_name (str): Name of the .engram file
            file_path (Path): Full path to the .engram file
        """
        try:
            # Load the TOML content
            with file_path.open('rb') as f:
                engram_data = tomli.load(f)

            engram_id = engram_data['engram'][0]['id']
            engram = self.engram_repository.fetch_engram(engram_id)

            if engram is None:
                logging.info('Loaded .engram file: %s', file_path)
                logging.debug('Engram data: %s', engram_data)
                engram_data.update({'parent_id': None})
                engram_data.update({'tracking_id': ''})

                engram_data['engram'][0]['context'] = json.loads(engram_data['engram'][0]['context'])

                observation = self.observation_repository.load_toml_dict(engram_data)

                async def send_message() -> Observation:
                    self.send_message_async(
                        Service.Topic.OBSERVATION_CREATED, {'id': observation.id, 'parent_id': None}
                    )

                    return observation

                task = self.run_task(send_message())
                task.add_done_callback(self._on_observation_created_complete)

                # TODO: Process the loaded TOML data according to .engram file schema

        except (FileNotFoundError, PermissionError):
            logging.warning("Could not read .engram file '%s'", file_path)
        except tomli.TOMLDecodeError:
            logging.exception("Invalid TOML format in .engram file '%s'", file_path)
        except Exception:
            logging.exception("Unexpected error loading .engram file '%s'", file_path)

    def _on_observation_created_complete(self, ret: Future[Any]) -> None:
        observation = ret.result()
        self.send_message_async(Service.Topic.OBSERVATION_COMPLETE, asdict(observation))

    def _on_update_repo_files_complete(self, ret: Future[Any]) -> None:
        """
        Callback when the update_repo_files task completes.

        Args:
            ret (Future[Any]): Future object representing the completed task.
        """
        ret.result()
