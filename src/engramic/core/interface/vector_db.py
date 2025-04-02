# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from abc import ABC, abstractmethod
from typing import Any

from engramic.core import Index


class VectorDB(ABC):
    """
    An abstract base class that defines an interface for any Large Language Model.
    """

    @abstractmethod
    def query(self, collection_name: str, embeddings: list[float], args: dict[str, Any]) -> dict[str, Any]:
        """
        Submits a prompt to the LLM and returns the model-generated text.

        Args:
            prompt (str): The prompt or input text for the LLM.
            **kwargs (Any): Optional keyword arguments for provider-specific settings,
                such as model name, temperature, max tokens, etc.

        Returns:
            str: The model-generated response.
        """

    @abstractmethod
    def insert(self, collection_name: str, index_list: list[Index], obj_id: str, args: dict[str, Any]) -> None:
        pass
