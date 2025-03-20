# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from __future__ import annotations

import cProfile
import logging
from typing import Any

from engramic.infrastructure.system.base_message_service import BaseMessageService
from engramic.infrastructure.system.host import Host  # noqa: TCH001
from engramic.infrastructure.system.service import Service


class MessageService(BaseMessageService):
    def __init__(self, host: Host) -> None:
        super().__init__(host)
        self.profiler: cProfile.Profile | None = None

    def init_async(self) -> None:
        super().init_async()
        self.profiler = None

    def start(self) -> None:
        self.subscribe(Service.Topic.START_PROFILER, self.start_profiler)
        self.subscribe(Service.Topic.END_PROFILER, self.end_profiler)

    def start_profiler(self, data: dict[Any, Any]) -> None:
        if data is not None:
            del data
        logging.info('Start Profiler')
        self.profiler = cProfile.Profile()
        if self.profiler:
            self.profiler.enable()

    def end_profiler(self, data: dict[Any, Any]) -> None:
        if data is not None:
            del data
        logging.info('Stop Profiler')
        if self.profiler:
            self.profiler.disable()
            self.profiler.dump_stats('profile_output.prof')
