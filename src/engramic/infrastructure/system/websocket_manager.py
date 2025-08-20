# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlparse

import jwt
from websockets.asyncio.server import Server, ServerConnection, serve

if TYPE_CHECKING:
    from engramic.core.host import Host
    from engramic.core.interface.llm import LLM


class WebsocketManager:
    def __init__(self, host: Host):
        self.active_connection: ServerConnection | None = None
        self.host = host
        self.server: Server | None = None

    def init_async(self) -> None:
        self.future = self.host.run_background(self.run_server())

    async def run_server(self) -> None:
        self.server = await serve(self.handler, 'localhost', 8765)
        await self.server.serve_forever()

    async def handler(self, websocket: ServerConnection) -> None:
        # 1. Extract token from path (e.g., ?token=abc123)

        if websocket.request is None:
            error = 'websocket.request is None but not expected to be.'
            raise RuntimeError(error)

        query = urlparse(websocket.request.path).query
        access_token = parse_qs(query).get('access_token', [None])[0]

        if access_token is None:
            error = 'Websocket did not contain token.'
            raise RuntimeError(error)

        access_token = access_token.strip()

        if not access_token:
            await websocket.close(code=4001, reason='Missing token')
            return

        # 2. Validate token
        try:
            payload = jwt.decode(access_token, os.getenv('JWT_SECRET_KEY'), algorithms=['HS256'])
            del payload
        except jwt.InvalidTokenError:
            await websocket.close(code=4002, reason='Invalid token')
            return

        self.active_connection = websocket

        await websocket.wait_closed()

        info = 'Websocket closed'
        logging.info(info)

    async def message_task(self, message: LLM.StreamPacket) -> None:
        if self.active_connection:
            await self.active_connection.send(str(message.packet))

    def send_message(self, message: LLM.StreamPacket) -> None:
        if self.active_connection:
            self.host.run_task(self.message_task(message))

    async def shutdown(self) -> None:
        """Gracefully shut down the websocket server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.server = None
            logging.debug('response web socket closed.')
