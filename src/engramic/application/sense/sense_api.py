# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engramic.infrastructure.system.service import Service


class SenseAPI:
    def __init__(self, service: Service) -> None:
        self.app = service.app
        # self.store = Store()
        self._setup_routes()

    def _setup_routes(self) -> None:
        @self.app.get('/hello')
        def hello() -> dict[str, str]:
            return {'message': 'Hello, World!'}
