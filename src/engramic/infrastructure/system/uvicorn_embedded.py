# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import threading
    from concurrent.futures import Future

    from fastapi import FastAPI

from typing import Final

import uvicorn


class UvicornEmbedded:
    def __init__(self, app: FastAPI, host: str = '127.0.0.1', port: int = 8001, log_level: str = 'info') -> None:
        cfg = uvicorn.Config(app=app, host=host, port=port, log_level=log_level, workers=1)
        self._server: Final[uvicorn.Server] = uvicorn.Server(cfg)
        self._thread: threading.Thread | None = None
        self._future: Future[None] | None = None

    async def serve(self) -> None:
        """Async method to serve the application"""
        try:
            await self._server.serve()
        except RuntimeError as e:
            exception = f'RuntimeError: {e}'
            raise RuntimeError(exception) from e

    async def shutdown(self) -> None:
        #    """Shutdown the embedded uvicorn server"""
        if self._server:
            self._server.should_exit = True
            await self._server.shutdown()
