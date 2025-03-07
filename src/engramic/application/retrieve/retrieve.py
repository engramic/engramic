# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import asyncio
import logging

from engramic.infrastructure.system.service import Service


class Retrieve(Service):
    ITERATIONS = 3

    def __init__(self)->None:
        super().__init__()
        self.finished = False

    async def _task(self) -> None:
        ctr = 0
        while ctr < self.ITERATIONS:
            logging.info('Running async task...')
            ctr += 1
            await asyncio.sleep(2)

        self.finished = True

    def start(self) -> None:
        """Start the service and add a background task."""
        super().start()
        self.submit_async_task(self._task())
