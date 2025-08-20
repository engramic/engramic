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
import shutil
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING, Any

import tomli

from engramic.core.file_node import FileNode
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
        file_node_index (dict[str, Any]): Index of all files by document ID.
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
        self.file_node_index: dict[str, Any] = {}  # memory copy of all files and folders across the system
        self.submitted_documents: set[str] = set()

    def start(self) -> None:
        """
        Starts the repository service and subscribes to relevant topics.
        """
        self.subscribe(Service.Topic.REPO_SUBMIT_IDS, self._on_scan_ids)
        self.subscribe(Service.Topic.REPO_UPDATE_REPOS, self.scan_folders)
        self.subscribe(Service.Topic.REPO_ADD_REPO, self._on_repo_create)
        self.subscribe(Service.Topic.REPO_DELETE_FILE, self._on_delete_file_node)
        self.subscribe(Service.Topic.REPO_ADD_FILE, self._on_add_file_node)
        super().start()

        async def scan_folders() -> None:
            self.scan_folders()

        self.run_task(scan_folders())

    def init_async(self) -> None:
        """
        Initializes asynchronous components of the service.
        """
        return super().init_async()

    def _on_delete_file_node(self, msg: dict[str, Any]) -> None:
        file_node = FileNode(**msg)

        repo_root = os.path.expanduser(os.environ.get('REPO_ROOT', ''))

        # Construct file path
        file_path = Path(os.path.join(repo_root, *file_node.file_dirs, file_node.file_name))

        # Delete based on node_type
        if file_path.exists():
            if file_node.node_type == 'folder':
                # Delete folder and all its contents recursively

                shutil.rmtree(file_path)  # replace this with a call to S3 or similar.
            else:
                # Delete file
                file_path.unlink()  # replace this with a call to S3 or similar.
                self.document_repository.delete(file_node.id)

        if file_node.repo_id is None:
            error = 'Filenode.repo_id is None but not expected to be.'
            raise RuntimeError(error)

        repo = self.repos[file_node.repo_id]
        self.scan_folders(asdict(repo))

    def _on_add_file_node(self, msg: dict[str, Any]) -> None:
        repo_id = msg['repo_id']
        file_name = msg['file_name']
        file_dirs = msg['file_dirs']

        file_node = FileNode(FileNode.Root.DATA.value, file_name, FileNode.Type.FILE.value, file_dirs)
        self.document_repository.save(file_node)

        async def send_message() -> None:
            self.send_message_async(Service.Topic.REPO_UPDATE_REPOS, {'repo_id': repo_id})

        self.run_task(send_message())

    def _on_scan_ids(self, msg: dict[str, Any]) -> None:
        """
        Handles the REPO_SUBMIT_IDS message.

        Args:
            msg (str): JSON message containing document IDs to submit.
        """
        id_array = msg['submit_ids']
        overwrite = False

        if 'overwrite' in msg:
            overwrite = msg['overwrite']

        self.scan_ids(id_array, overwrite=overwrite)

    def scan_ids(self, id_array: list[str], *, overwrite: bool = False) -> None:
        """
        Submits documents for processing by their IDs.

        Args:
            id_array (list[str]): List of document IDs to submit.
            overwrite (bool): Whether to overwrite existing documents. Defaults to False.
        """
        for sub_id in id_array:
            if sub_id in self.file_node_index:
                document = self.file_node_index[sub_id]

                self.send_message_async(
                    Service.Topic.DOCUMENT_SCAN_DOCUMENT, {'document': asdict(document), 'overwrite': overwrite}
                )
                self.submitted_documents.add(document.id)
            else:
                error = f'Scan ID called on id {sub_id} but document is not found.'
                logging.error(error)

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

    def _on_repo_create(self, msg: dict[str, Any]) -> None:
        """
        Handles repository creation by creating a new folder with a .repo configuration file.

        Args:
            msg (str): JSON message containing the repository name.
        """
        try:
            repo_name = msg['repo_name']

            # Get the repository root path
            repo_root = self._get_repo_root()

            # Create the new repository folder
            repo_folder = repo_root / repo_name
            repo_folder.mkdir(parents=True, exist_ok=True)

            # Generate a new UUID for the repository
            repo_id = str(uuid.uuid4())

            # Create the .repo file content
            repo_config = f"""[repository]
id = "{repo_id}"
"""

            # Write the .repo file
            repo_file = repo_folder / '.repo'
            with repo_file.open('w', encoding='utf-8') as f:
                f.write(repo_config)

            # Add the new repository to our in-memory index
            self.repos[repo_id] = Repo(name=repo_name, repo_id=repo_id, is_default=False)

            # Send message to update the UI
            self.send_message_async(
                Service.Topic.REPO_DIRECTORY_SCANNED,
                {'repos': {repo_id: asdict(self.repos[repo_id]) for repo_id in self.repos}},
            )

            system_repo_root = os.getenv('REPO_ROOT')
            if system_repo_root:
                env_root = Path(system_repo_root)
                repo_file_folder_tree = self._index_repo_files(repo_id, repo_name, env_root)
                future = self.run_task(self.update_repo_files(repo_id, repo_file_folder_tree))
                future.add_done_callback(self._on_update_repo_files_complete)

                logging.info("Created new repository '%s' with ID '%s'", repo_name, repo_id)

        except (json.JSONDecodeError, KeyError):
            logging.exception(
                'Invalid message format for repo creation',
            )
        except (OSError, PermissionError):
            logging.exception('Failed to create repository folder:')
        except Exception:
            logging.exception('Unexpected error creating repository:')

    def _traverse_file_folder_tree(self, tree_node: dict[str, Any]) -> dict[str, Any]:
        """
        Traverse the file_folder_tree and collect all files and folders.

        Args:
            tree_node (dict[str, Any]): The tree node to traverse

        Returns:
            dict[str, Any]: Dictionary containing all files and folders indexed by their IDs
        """
        files_and_folders = {}

        # Add folder to collection if it has an ID
        if tree_node.get('folder_id') is not None:
            folder_id = tree_node['folder_id']
            if folder_id in self.file_node_index:
                file_node = self.file_node_index[folder_id]
                files_and_folders[folder_id] = asdict(file_node)

        # Add all files in current node
        for file_id in tree_node.get('files', []):
            if file_id in self.file_node_index:
                file_node = self.file_node_index[file_id]
                files_and_folders[file_id] = asdict(file_node)

        # Recursively traverse subfolders
        for subfolder in tree_node.get('folders', []):
            subfolder_files_and_folders = self._traverse_file_folder_tree(subfolder)
            files_and_folders.update(subfolder_files_and_folders)

        return files_and_folders

    async def update_repo_files(self, repo_id: str, file_folder_tree: dict[str, Any]) -> None:
        """
        Updates the list of files for a repository.

        Args:
            repo_id (str): ID of the repository to update.
            file_folder_tree (dict[str, Any]): The hierarchical tree structure of files and folders.
            repo_files_and_folders (dict[str, Any], optional): Pre-computed files and folders dict.
        """

        # If repo_files_and_folders is not provided, traverse the tree to collect it
        repo_files_and_folders = self._traverse_file_folder_tree(file_folder_tree)

        self.send_message_async(
            Service.Topic.REPO_FILE_FOLDER_TREE_UPDATED,
            {
                'repo': asdict(self.repos[repo_id]),
                'file_tree': file_folder_tree,
                'files_and_folders': repo_files_and_folders,
            },
        )

    def scan_folders(self, repo: dict[str, str] | None = None) -> None:
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
        repos_to_scan = self._determine_repos_to_scan(repo, repo_root)

        self._send_repo_directory_scanned()
        self._scan_and_index_repos(repos_to_scan, repo_root)

    def _get_repo_root(self) -> Path:
        """Get and validate the repository root path."""
        repo_root = os.getenv('REPO_ROOT')
        if repo_root is None:
            error = "Environment variable 'REPO_ROOT' is not set."
            raise RuntimeError(error)
        return Path(repo_root).expanduser()

    def _determine_repos_to_scan(self, repo: dict[str, str] | None, repo_root: Path) -> dict[str, Repo]:
        """Determine which repositories need to be scanned."""
        target_repo_id = repo.get('repo_id') if repo is not None else None

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

    def _send_repo_directory_scanned(self) -> None:
        """Send async message with repository folders."""

        async def send_message() -> None:
            # Convert Repo objects to dictionaries for serialization
            repos_dict = {repo_id: asdict(repo) for repo_id, repo in self.repos.items()}
            self.send_message_async(Service.Topic.REPO_DIRECTORY_SCANNED, {'repos': repos_dict})

        self.run_task(send_message())

    def _scan_and_index_repos(self, repos_to_scan: dict[str, Repo], system_repo_root: Path) -> None:
        """Scan and index files in the specified repositories."""
        for current_repo_id, repo in repos_to_scan.items():
            repo_file_folder_tree = self._index_repo_files(current_repo_id, repo.name, system_repo_root)

            future = self.run_task(self.update_repo_files(current_repo_id, repo_file_folder_tree))
            future.add_done_callback(self._on_update_repo_files_complete)

    # store all files and folders in file_node_index

    def _index_repo_files(self, repo_id: str, repo_name: str, system_repo_root: Path) -> dict[str, Any]:
        """Index all files and folders in a repository folder."""
        repo_root_object = self._create_folder_node(repo_id, repo_name, '', [])

        if repo_root_object is None:
            error = 'Expected an id but None was found.'
            raise RuntimeError(error)

        self.file_node_index[repo_root_object.id] = repo_root_object

        tree_root = {'folder_id': repo_root_object.id, 'folder_name': '', 'files': [], 'folders': []}

        # Keep track of folder nodes by their path for tree building
        folder_nodes: dict[str, Any] = {str(system_repo_root / repo_name): tree_root}

        # Create folder nodes for each directory
        for absolute_dir_path, dirs, files in os.walk(system_repo_root / repo_name):
            current_path = str(Path(absolute_dir_path))
            current_node = folder_nodes.get(current_path, tree_root)

            # Calculate the relative path from repo root to build dir_list
            relative_root = Path(absolute_dir_path).relative_to(system_repo_root / repo_name)
            dir_list = list(relative_root.parts) if relative_root != Path('.') else []

            self._process_subdirectories(
                dirs, repo_id, repo_name, dir_list, absolute_dir_path, current_node, folder_nodes
            )
            self._process_files(files, system_repo_root, repo_id, repo_name, dir_list, current_node)

        return tree_root

    def _process_subdirectories(
        self,
        dirs: list[str],
        repo_id: str,
        repo_name: str,
        dir_list: list[str],
        absolute_dir_path: str,
        current_node: dict[str, Any],
        folder_nodes: dict[str, Any],
    ) -> None:
        for dir_name in dirs:
            if dir_name.startswith('.'):
                continue  # Skip hidden directories

            folder_node = self._create_folder_node(repo_id, repo_name, dir_name, dir_list)
            if folder_node is not None:
                self.file_node_index[folder_node.id] = folder_node

                # Create the folder entry in the tree
                folder_entry = {
                    'folder_id': folder_node.id,
                    'folder_name': folder_node.file_name,
                    'files': [],
                    'folders': [],
                }

                if not isinstance(current_node['folders'], list):
                    current_node['folders'] = []
                elif current_node['folders'] and isinstance(current_node['folders'][0], str):
                    # If it's a list of strings, clear it
                    current_node['folders'] = []

                current_node['folders'].append(folder_entry)

                # Map the full path to this folder entry for future reference
                dir_path = str(Path(absolute_dir_path) / dir_name)
                folder_nodes[dir_path] = folder_entry

    def _process_files(
        self,
        files: list[str],
        system_repo_root: Path,
        repo_id: str,
        repo_name: str,
        dir_list: list[str],
        current_node: dict[str, Any],
    ) -> None:
        for file in files:
            if file.startswith('.'):
                continue  # Skip hidden files

            doc = self._handle_file_by_type(str(system_repo_root), repo_id, repo_name, file, dir_list)
            if doc is not None:
                self.file_node_index[doc.id] = doc
                current_node['files'].append(doc.id)

    def _create_folder_node(self, repo_id: str, repo_name: str, dir_name: str, dir_list: list[str]) -> FileNode | None:
        """Create a File_ode object for folders."""

        folder_node = FileNode(
            root_directory=FileNode.Root.DATA.value,
            file_dirs=[repo_name, *dir_list],
            file_name=dir_name,
            node_type=FileNode.Type.FOLDER.value,
            repo_id=repo_id,
        )

        return folder_node

    def _handle_file_by_type(
        self, system_repo_root: str, repo_id: str, repo_name: str, file_name: str, folder_dir_list: list[str]
    ) -> FileNode | None:
        """Handle different file types and return a FileNode if applicable."""

        # Handle different file types
        file_extension = Path(file_name).suffix.lower()

        if file_extension == '.pdf':
            return self._create_document_from_pdf(repo_id, [repo_name, *folder_dir_list], file_name)
        if file_extension == '.engram':
            self._load_engram_file(system_repo_root, [repo_name, *folder_dir_list], file_name)
            return None
        # For other file types, create a generic file node
        return None

    def _create_document_from_pdf(self, repo_id: str, folder_dir_list: list[str], file_name: str) -> FileNode:
        """Create a FileNode object for PDF files."""
        doc = FileNode(
            root_directory=FileNode.Root.DATA.value,
            file_dirs=folder_dir_list,
            file_name=file_name,
            node_type=FileNode.Type.FILE.value,
            repo_id=repo_id,
        )

        # Check to see if the document has been loaded before.
        fetched_doc: dict[str, Any] = self.document_repository.load(doc.id)

        # If it has been found before, then use that version.
        if len(fetched_doc['document']) != 0:
            doc = FileNode(**fetched_doc['document'][0])
        else:
            self.document_repository.save(doc)

            # TODO: Need to make this run once.
            async def send_message() -> None:
                self.send_message_async(
                    Service.Topic.REPO_FILE_FOUND, {'document_id': doc.id, 'tracking_id': doc.tracking_id}
                )

            self.run_task(send_message())

        return doc

    def _load_engram_file(self, system_repo_root: str, file_list: list[str], file_name: str) -> None:
        """
        Load an .engram TOML file.
        """
        file_path = Path(system_repo_root, *file_list, file_name)  # <-- Use Path here

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
