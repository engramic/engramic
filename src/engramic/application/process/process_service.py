# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

"""
Provides services for generating educational content and lessons from documents.
"""

from dataclasses import asdict
from typing import Any

from engramic.application.process.trigger_set import TriggerSet
from engramic.core.host import Host
from engramic.core.process import Process
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
        super().__init__(host)

    def init_async(self) -> None:
        return super().init_async()

    def start(self) -> None:
        self.subscribe(Service.Topic.PROGRESS_PROGRESS_UPDATED, self._on_process_progress_updated)
        self.trigger_command = TriggerSet(self, [Service.Topic.PROCESS_CMD])
        self.trigger_file_found_trigger = TriggerSet(self, [Service.Topic.REPO_FILE_FOUND])

        ret_val = self.process_repository.load_most_recent(10)

        async def send_message() -> None:
            self.send_message_async(
                Service.Topic.PROCESS_RECENT_PROCESS_UPDATED, {'recent_processes': ret_val['process']}
            )

        self.run_task(send_message())
        super().start()

    def _on_process_progress_updated(self, msg: dict[str, Any]) -> None:
        tracking_id = msg['tracking_id']
        if tracking_id in self.active_processes:
            process = self.active_processes[tracking_id]
            process.percent_complete = msg['percent_complete']

            if process.percent_complete >= 1.0:
                process.status = Process.Status.DONE.value
                self.process_repository.save(process)
                self.send_message_async(
                    Service.Topic.PROCESS_RECENT_PROCESS_UPDATED, {'recent_processes': [asdict(process)]}
                )
            else:
                process.status = Process.Status.RUNNING.value

            self.send_message_async(Service.Topic.PROCESS_PROGRESS_UPDATED, asdict(process))
