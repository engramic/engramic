# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.


from typing import TYPE_CHECKING

from engramic.application.retrieve.ask import Ask
from engramic.core import Prompt
from engramic.infrastructure.system.service import Service

if TYPE_CHECKING:
    from engramic.infrastructure.system.plugin_manager import PluginManager


class RetrieveService(Service):
    # ITERATIONS = 3

    def __init__(self) -> None:
        super().__init__()
        self.host: PluginManager = None

    def start(self, host) -> None:
        """Start the service and add a background task."""
        self.host = host
        super().start(host)

    def submit(self, prompt: Prompt) -> None:
        retrieval = Ask(prompt, self.host.get_plugin_manager())
        retrieval.get_sources(super())
