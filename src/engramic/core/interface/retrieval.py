# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from abc import ABC, abstractmethod


class Retrieval(ABC):
    id: str

    @abstractmethod
    def get_sources(self) -> None:
        pass
