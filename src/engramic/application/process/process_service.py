# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

"""
Provides services for generating educational content and lessons from documents.
"""

import logging
import uuid
from dataclasses import asdict
from typing import Any

from engramic.application.process.process import FileInfoPass, FinalPromptPass, Process, ScanFilePass
from engramic.core.host import Host
from engramic.core.prompt import Prompt
from engramic.infrastructure.repository.process_repository import ProcessRepository
from engramic.infrastructure.system.service import Service


class ProcessService(Service):
    """
    Service that performs a structured process on a file or repo.
    """

    def __init__(self, host: Host) -> None:
        db_plugin = host.plugin_manager.get_plugin('db', 'document')
        self.process_repository: ProcessRepository = ProcessRepository(db_plugin)
        self.active_processes: dict[str, Process] = {}

        self.files_and_folders_by_repo: dict[str, list[Any]] = {}
        self.file_folder_trees: dict[str, Any] = {}

        super().__init__(host)

    def init_async(self) -> None:
        return super().init_async()

    def start(self) -> None:
        self.subscribe(Service.Topic.REPO_FILE_FOUND, self._on_repo_file_found)
        self.subscribe(Service.Topic.PROCESS_RUN_PROCESS, self._on_run_process)
        self.subscribe(Service.Topic.PROCESS_CREATE, self._on_process_create)
        self.subscribe(Service.Topic.PROGRESS_PROGRESS_UPDATED, self._on_progress_progress_updated)
        self.subscribe(Service.Topic.REPO_FILE_FOLDER_TREE_UPDATED, self._on_repos_file_folder_tree_updated)

        # update external systems
        ret_val = self.process_repository.load_most_recent(10)

        async def send_message() -> None:
            self.send_message_async(
                Service.Topic.PROCESS_RECENT_PROGRESS_UPDATED, {'recent_progress_list': ret_val['process']}
            )

        self.run_task(send_message())
        super().start()

    def _on_process_create(self, msg: dict[str, Any]) -> None:
        process_type = str(msg.get('process_type')) if msg.get('process_type') is not None else None
        input_prompt = str(msg.get('input_prompt'))

        selected_repos = msg.get('selected_repos', [])
        conversation_id = msg.get('conversation_id')
        widget_cmd = msg.get('widget_cmd')
        client_id = msg.get('client_id')
        thinking_level = msg.get('thinking_level')
        target_single_file = msg.get('target_single_file')

        input_prompt_obj = Prompt(
            prompt_str=input_prompt,
            widget_cmd=widget_cmd,
            repo_ids_filters=selected_repos,
            include_default_repos=True,
            conversation_id=conversation_id,
            thinking_level=thinking_level,
            target_single_file=target_single_file,
        )

        process = self.build_process(process_type, input_prompt_obj, client_id)
        self.process_repository.save(process)
        process.start_process(self)

    def _on_repo_file_found(self, msg: dict[str, Any]) -> None:
        process = self.build_process(Process.ProcessType.SCAN.value, None)
        process.document_id = msg['document_id']
        process.current_tracking_id = msg['tracking_id']

        if process.current_tracking_id is None:
            error = 'Current tracking id is none but not expected to be.'
            raise RuntimeError(error)

        self.active_processes[process.current_tracking_id] = process
        self.process_repository.save(process)
        process.start_process(self)

    def _on_run_process(self, msg: dict[str, Any]) -> None:
        input_prompt = Prompt(**msg['input_prompt'])
        process_type = msg['process_type']
        process = self.build_process(process_type, input_prompt)
        process.current_tracking_id = str(uuid.uuid4())
        self.active_processes[process.current_tracking_id] = process
        self.process_repository.save(process)
        process.start_process(self)

    def build_process(
        self, process_name: str | None, input_prompt: Prompt | None, client_id: str | None = None
    ) -> Process:
        process = None
        process_id = str(uuid.uuid4())

        if process_name == Process.ProcessType.PROMPT_ONLY.value or process_name is None:
            process_name = Process.ProcessType.PROMPT_ONLY.value
            if input_prompt is None:
                error = 'Input prompt is None but not expected to be.'
                raise RuntimeError(error)

            process = Process(process_name, process_id, 0.0, pass_array=[FinalPromptPass(input_prompt=input_prompt)])
        if process_name == Process.ProcessType.SCAN.value:
            process = Process(process_name, process_id, 0.0, pass_array=[ScanFilePass()])
        if process_name == Process.ProcessType.REPO_FILE_INFO.value:
            if input_prompt is None:
                error = 'input_prompt None but expected not to be.'
                raise RuntimeError(error)

            process = Process(
                process_name,
                process_id,
                0.0,
                pass_array=[
                    FileInfoPass(
                        input_prompt=input_prompt,
                        files_and_folders_by_repo=self.files_and_folders_by_repo,
                        file_folder_trees=self.file_folder_trees,
                    ),
                    FinalPromptPass(input_prompt=input_prompt),
                ],
            )

        if process is None:
            error = 'Failed to build process.'
            raise RuntimeError(error)

        if process:
            self.send_message_async(Service.Topic.PROCESS_ACTIVE_PROGRESS_UPDATED, asdict(process))

        if client_id and process:
            process.client_id = client_id

        return process

    def _on_progress_progress_updated(self, msg: dict[str, Any]) -> None:
        tracking_id = msg['tracking_id']
        if tracking_id in self.active_processes:
            process = self.active_processes[tracking_id]

            if process.failed_message:
                process.status = Process.Status.FAILED.value
                self.send_message_async(
                    Service.Topic.RESPONSE_SUBMIT_RESPONSE, {'user_response': process.failed_message}
                )
                return

            try:
                current_pass = process.pass_array[process.current_pass]
            except IndexError:
                logging.exception('Current pass index out of range for process %s', process.current_tracking_id)
                return

            current_pass.percent_complete = msg['percent_complete']

            if current_pass.percent_complete >= 1.0:
                process.current_pass += 1

                if len(process.pass_array) == process.current_pass:
                    process.status = Process.Status.DONE.value
                    process.percent_complete = 1
                    self.process_repository.save(process)
                else:
                    process.percent_complete = process.current_pass / len(process.pass_array)
                    del self.active_processes[tracking_id]

                    new_tracking_id = process.pass_array[process.current_pass].execute(self, process)

                    if new_tracking_id is None:
                        error = 'New tracking id is None but expected not to be.'
                        raise RuntimeError(error)

                    self.active_processes[new_tracking_id] = process

                self.send_message_async(Service.Topic.PROCESS_ACTIVE_PROGRESS_UPDATED, asdict(process))
                self.send_message_async(
                    Service.Topic.PROCESS_RECENT_PROGRESS_UPDATED, {'recent_progress_list': [asdict(process)]}
                )
            else:
                process.status = Process.Status.RUNNING.value

            self.send_message_async(Service.Topic.PROCESS_ACTIVE_PROGRESS_UPDATED, asdict(process))

    def _on_repos_file_folder_tree_updated(self, msg: dict[str, Any]) -> None:
        repo = msg['repo']
        files_tree = msg['file_tree']
        file_and_folder_list = msg['files_and_folders']

        self.file_folder_trees[repo['repo_id']] = files_tree
        self.files_and_folders_by_repo[repo['repo_id']] = file_and_folder_list
