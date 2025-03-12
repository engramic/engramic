# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from abc import ABC, abstractmethod

from engramic.core.prompt import Prompt


class Retrieval(ABC):
    class RetrievalResponse:
        def __init__(self, set_in: set) -> None:
            self.set = set_in

    @abstractmethod
    def get_sources(self, prompt: Prompt) -> RetrievalResponse:
        pass
