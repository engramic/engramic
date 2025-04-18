# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from __future__ import annotations

import cProfile
import logging
import time
from typing import TYPE_CHECKING, Any

from engramic.infrastructure.system.base_message_service import BaseMessageService
from engramic.infrastructure.system.service import Service

if TYPE_CHECKING:
    from engramic.core.host import Host
    from engramic.core.metrics_tracker import MetricPacket


class MessageService(BaseMessageService):
    """
    A system-level message handling service that provides runtime profiling capabilities and reports metrics.

    The MessageService listens for system-level control messages, such as those initiating or ending
    profiling sessions, and acknowledgment messages for metrics reporting. It extends BaseMessageService
    to provide core message routing functionality, with additional support for CPU profiling via `cProfile`.

    Attributes:
        profiler (cProfile.Profile | None): An optional CPU profiler instance used to monitor performance
            during execution. Initialized and controlled via START_PROFILER and END_PROFILER messages.

    Methods:
        init_async(): Initializes the service asynchronously, resetting any existing profiler instance.
        start(): Subscribes to system topics to enable profiler control and metric acknowledgment.
        stop(): Stops the message service.
        start_profiler(data): Starts the CPU profiler if not already running.
        end_profiler(data): Stops the CPU profiler and writes the profiling data to a file.
        on_acknowledge(message_in): Sends a status update containing tracked metrics upon acknowledgment.
    """

    def __init__(self, host: Host) -> None:
        super().__init__(host)
        self.profiler: cProfile.Profile | None = None

    def init_async(self) -> None:
        super().init_async()
        self.profiler = None

    def start(self) -> None:
        self.subscribe(Service.Topic.ACKNOWLEDGE, self.on_acknowledge)
        self.subscribe(Service.Topic.START_PROFILER, self.start_profiler)
        self.subscribe(Service.Topic.END_PROFILER, self.end_profiler)
        super().start()

    async def stop(self) -> None:
        await super().stop()

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

    def on_acknowledge(self, message_in: str) -> None:
        del message_in

        metrics_packet: MetricPacket = self.metrics_tracker.get_and_reset_packet()

        self.send_message_async(
            Service.Topic.STATUS,
            {'id': self.id, 'name': self.__class__.__name__, 'timestamp': time.time(), 'metrics': metrics_packet},
        )
