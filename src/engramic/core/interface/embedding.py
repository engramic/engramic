# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from abc import ABC, abstractmethod
from typing import Any


class Embedding(ABC):
    """
    An abstract base class that defines an interface for any embedding API.
    """

    @abstractmethod
    def gen_embed(self, strings: list[str], args: dict[str, Any]) -> dict[str, list[list[float]]]:
        """
        Submits a prompt to the embedding API and returns the model-generated text.

        Args:
            indices list[str] a list of strings to be embedded.

        Returns:
            str: The model-generated embedding.
        """
