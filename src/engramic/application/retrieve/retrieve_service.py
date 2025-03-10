# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import logging

from engramic.core import Retrieval
from engramic.infrastructure.system.service import Service


class RetrieveService(Service):
    # ITERATIONS = 3

    def __init__(self) -> None:
        super().__init__()

    def start(self,host) -> None:
        """Start the service and add a background task."""
        super().start(host)

    def submit(self, retrieval: Retrieval):
        retrieval.get_sources(super())

