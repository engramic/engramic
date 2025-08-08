# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from engramic.core.prompt import Prompt
from engramic.infrastructure.system.service import Service

if TYPE_CHECKING:
    from engramic.application.process.process_service import ProcessService


@dataclass(kw_only=True)
class ProcessPass(ABC):
    percent_complete: float = 0.0

    @abstractmethod
    def execute(self, process_service: ProcessService, process: Process) -> str | None:
        pass

    def update_progress(
        self, process_service: ProcessService, process: Process, percent_complete: float, tracking_id: str
    ) -> str:
        process.percent_complete = percent_complete
        process_service.send_message_async(
            Service.Topic.PROGRESS_PROGRESS_UPDATED,
            {'tracking_id': tracking_id, 'percent_complete': percent_complete},
        )
        return tracking_id


@dataclass(kw_only=True)
class ResponseOnlyPass(ProcessPass):
    prompt_str: str
    repo_ids_filters: list[str]

    def execute(self, process_service: ProcessService, process: Process) -> str:
        del process

        process_service.send_message_async(Service.Topic.RESPONSE_SUBMIT_RESPONSE, {'user_response': self.prompt_str})

        tracking_id = str(uuid.uuid4())
        process_service.send_message_async(
            Service.Topic.PROGRESS_PROGRESS_UPDATED, {'tracking_id': tracking_id, 'percent_complete': 1.0}
        )  # bypass progress system, it's not needed.

        return tracking_id


@dataclass(kw_only=True)
class BasicPromptPass(ProcessPass):
    prompt_str: str
    repo_ids_filters: list[str]

    def execute(self, process_service: ProcessService, process: Process) -> str:
        del process
        simple_prompt = Prompt(self.prompt_str, repo_ids_filters=self.repo_ids_filters, include_default_repos=False)
        process_service.send_message_async(Service.Topic.SUBMIT_PROMPT, asdict(simple_prompt))
        if simple_prompt.tracking_id is None:
            error = 'Tracking_id is none but expected not to be.'
            raise RuntimeError(error)

        return simple_prompt.tracking_id


@dataclass(kw_only=True)
class FinalPromptPass(ProcessPass):
    input_prompt: Prompt

    def execute(self, process_service: ProcessService, process: Process) -> str:
        if process.memory:
            self.input_prompt.prompt_str += ' ' + str(process.memory)

        process_service.send_message_async(Service.Topic.SUBMIT_PROMPT, asdict(self.input_prompt))
        if self.input_prompt.tracking_id is None:
            error = 'Tracking_id is none but expected not to be.'
            raise RuntimeError(error)

        return self.input_prompt.tracking_id


@dataclass(kw_only=True)
class FileInfoPass(ProcessPass):
    input_prompt: Prompt
    files_and_folders_by_repo: dict[str, Any]
    file_folder_trees: dict[str, Any]

    def execute(self, process_service: ProcessService, process: Process) -> str:
        repo_ids = self.input_prompt.repo_ids_filters

        if repo_ids is None:
            process.failed_message = "Tell the user that you can't do a file lookup unless they select a repo."
            return self.update_progress(process_service, process, 1.0, str(uuid.uuid4()))

        # Initialize as empty lists/dicts if not already present
        process.memory.setdefault('Repos', {})

        for repo_id in repo_ids:
            # Generate human-readable tree and save to memory
            tree_text = self._build_readable_tree(
                self.file_folder_trees[repo_id], self.files_and_folders_by_repo[repo_id]
            )
            process.memory['Repos'][repo_id] = tree_text

        tracking_id = str(uuid.uuid4())
        self.update_progress(process_service, process, 1.0, tracking_id)
        return str(tracking_id)

    def _build_readable_tree(
        self, tree_structure: dict[str, Any], file_metadata: dict[str, Any], indent: str = ''
    ) -> str:
        """Build a human-readable tree representation of the file structure."""
        lines = []

        # Get folder name from metadata
        folder_info = file_metadata.get(tree_structure['folder_id'], {})
        folder_name = folder_info.get('file_name', folder_info.get('root_directory', 'Root'))

        if folder_name:
            lines.append(f'{indent}📁 {folder_name}/')

        # Add files in current folder
        for file_id in tree_structure.get('files', []):
            file_info = file_metadata.get(file_id, {})
            file_name = file_info.get('file_name', f'Unknown file ({file_id})')
            lines.append(f'{indent}├── 📄 {file_name}')

        # Add subfolders recursively
        for subfolder in tree_structure.get('folders', []):
            subfolder_tree = self._build_readable_tree(subfolder, file_metadata, indent + '│   ')
            lines.append(subfolder_tree)

        return '\n'.join(lines)


@dataclass(kw_only=True)
class ScanFilePass(ProcessPass):
    def execute(self, process_service: ProcessService, process: Process) -> str | None:
        process_service.send_message_async(Service.Topic.REPO_SUBMIT_IDS, {'submit_ids': [process.document_id]})
        return process.current_tracking_id


@dataclass
class Process:
    class ProcessType(Enum):
        PROMPT_ONLY = 'prompt_only'
        SCAN = 'scan'
        REPO_FILE_INFO = 'repo_file_info'

    class Status(Enum):
        INIT = 'init'
        PREP = 'prep'
        RUNNING = 'running'
        DONE = 'done'
        FAILED = 'failed'

    process_name: str
    id: str
    percent_complete: float
    pass_array: list[ProcessPass]
    document_id: str | None = None
    current_tracking_id: str | None = None
    start_time: int = field(default_factory=lambda: int(time.time()))
    status: str = Status.INIT.value
    current_pass: int = 0
    memory: dict[str, Any] = field(default_factory=dict[str, Any])
    client_id: str | None = None
    failed_message: str | None = None

    def start_process(self, process_service: ProcessService) -> None:
        process_pass = self.pass_array[self.current_pass]
        tracking_id = process_pass.execute(process_service, self)
        if tracking_id is None:
            error = 'Tracking_id is None but expected not to be.'
            raise RuntimeError(error)

        process_service.active_processes[tracking_id] = self
