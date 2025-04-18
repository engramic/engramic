# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import websockets.asyncio.server
from websockets.asyncio.server import Server, ServerConnection  # noqa: TCH002

if TYPE_CHECKING:
    from engramic.core.host import Host
    from engramic.core.interface.llm import LLM


class WebsocketManager:
    def __init__(self, host: Host):
        self.websocket: Server | None = None
        self.active_connection: ServerConnection | None = None
        self.host = host

    def init_async(self) -> None:
        self.future = self.host.run_background(self.run_server())

    # async def stop(self) -> None:
    #    self.future.result()

    async def run_server(self) -> None:
        self.websocket = await websockets.serve(self.handler, 'localhost', 8765)
        await self.websocket.wait_closed()

    async def handler(self, websocket: ServerConnection) -> None:
        self.active_connection = websocket

        try:
            # Listen for incoming messages
            async for message in websocket:
                logging.info('Received: %s', message)

        except websockets.exceptions.ConnectionClosed:
            logging.info('Client disconnected')
        finally:
            self.active_connection = None

    async def message_task(self, message: LLM.StreamPacket) -> None:
        if self.active_connection:
            await self.active_connection.send(str(message.packet))

    def send_message(self, message: LLM.StreamPacket) -> None:
        if self.active_connection:
            self.host.run_task(self.message_task(message))

    async def shutdown(self) -> None:
        """Gracefully shut down the websocket server."""
        if self.websocket:
            self.websocket.close()
            await self.websocket.wait_closed()
            self.websocket = None
            logging.debug('response web socket closed.')
