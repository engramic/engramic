# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.
from __future__ import annotations

import uuid
from dataclasses import asdict
from typing import TYPE_CHECKING, Any

from engramic.core.process import Process
from engramic.infrastructure.system.service import Service

if TYPE_CHECKING:
    from engramic.application.process.process_service import ProcessService


class TriggerSet:
    def __init__(self, process_service: ProcessService, topic_array: list[Service.Topic], cmd: str | None = None):
        self.process_service = process_service
        self.topic_array = topic_array
        self.cmd = cmd

        for topic in self.topic_array:
            if topic == Service.Topic.PROCESS_CMD:
                process_service.subscribe(Service.Topic.PROCESS_CMD, self._on_command)
            if topic == Service.Topic.REPO_FILE_FOUND:
                process_service.subscribe(Service.Topic.REPO_FILE_FOUND, self._on_file_found)

    def _on_command(self, msg: dict[str, Any]) -> None:
        command = msg['cmd']
        del command
        # repo_ids_filters = msg['repo_ids_filters']
        # tracking_id = msg['tracking_id']
        # process_id = str(uuid.uuid4())
        # process = Process("list-files",process_id,0.0)

        # ret_val = self.process_service.process_repository.save(process)

        # prompt = Prompt(prompt_str='Here is a list of files: eric.pdf',
        #                 widget_cmd=command,
        #                 repo_ids_filters=repo_ids_filters,
        #                 tracking_id=process_id,
        #                 is_background=True #super important to not prevent recursive behavior
        #                 )

        # self.process_service.send_message_async(Service.Topic.SUBMIT_PROMPT,asdict(prompt))

    def _on_file_found(self, msg: dict[str, Any]) -> None:
        document_id = msg['document_id']
        process_id = str(uuid.uuid4())
        tracking_id = msg['tracking_id']
        process = Process('scan', process_id, 0.01, document_id)
        self.process_service.active_processes[tracking_id] = process

        self.process_service.process_repository.save(process)

        self.process_service.send_message_async(Service.Topic.PROCESS_PROGRESS_UPDATED, asdict(process))

        self.process_service.send_message_async(Service.Topic.REPO_SUBMIT_IDS, {'submit_ids': [document_id]})
