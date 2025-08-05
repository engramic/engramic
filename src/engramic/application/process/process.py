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
    def execute(self, process_service: ProcessService, process: Process) -> str:
        pass


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
            error = 'Repo_ids is none but expected not to be.'
            raise RuntimeError(error)

        # Initialize as empty lists/dicts if not already present
        process.memory.setdefault('files', [])
        process.memory.setdefault('folder_tree', {})

        for repo_id in repo_ids:
            process.memory['files'].extend(self.files_and_folders_by_repo[repo_id])
            process.memory['folder_tree'][repo_id] = self.file_folder_trees[repo_id]

        tracking_id = str(uuid.uuid4())
        process_service.send_message_async(
            Service.Topic.PROGRESS_PROGRESS_UPDATED, {'tracking_id': tracking_id, 'percent_complete': 1.0}
        )  # bypass progress system.
        return str(tracking_id)


@dataclass(kw_only=True)
class ScanFilePass(ProcessPass):
    def execute(self, process_service: ProcessService, process: Process) -> str:
        process_service.send_message_async(Service.Topic.REPO_SUBMIT_IDS, {'submit_ids': [process.document_id]})
        return ''


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

    def start_process(self, process_service: ProcessService) -> str:
        process_pass = self.pass_array[self.current_pass]
        current_tracking_id = process_pass.execute(process_service, self)
        return current_tracking_id
