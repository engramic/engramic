# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from abc import ABC, abstractmethod


class Context(ABC):
    def __init__(self, context_dict: dict[str, str]):
        self.context_dict = context_dict

    @abstractmethod
    def render_context(self) -> str:
        """Abstract method that must be implemented by subclasses to render context meaningfully."""
