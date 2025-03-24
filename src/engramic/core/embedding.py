# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from abc import ABC, abstractmethod


class Embedding(ABC):
    """
    An abstract base class that defines an interface for any Large Language Model.
    """

    @abstractmethod
    def gen_embed(self, indices: list[str]) -> dict[str, list[str]]:
        """
        Submits a prompt to the LLM and returns the model-generated text.

        Args:
            prompt (str): The prompt or input text for the LLM.
            **kwargs (Any): Optional keyword arguments for provider-specific settings,
                such as model name, temperature, max tokens, etc.

        Returns:
            str: The model-generated response.
        """
