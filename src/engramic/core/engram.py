# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engramic.core.context import Context
    from engramic.core.index import Index


@dataclass()
class Engram:
    """
    Represents a unit of memory, consisting of a text string (such as a phrase, sentence, or paragraph)
    along with contextual information to help an LLM understand its domain relevance.

    Attributes:
        id (str): A unique identifier for the engram.
        location (str): The specific location or source of the engram such as a filepath.
        source_id (str): An identifier linking the engram to its originating source.
        content (str): The content of the engram in text.
        is_native_source (bool): Indicates whether the text is directly from the source (True) or derived from a previous response (False).
        context (Context | None): The contextual information associated with the engram.
        indices (list[Index] | None): A list of indices (text & embedding pair) related to the engram, this is used for semantic query.
        meta_id (str | None): A metadata identifier giving overview of the source document.
        library_id (str | None): An identifier linking the engram to a library, a collection of source documents.

    Methods:
        render_engram(): Returns a structured string representation of the engram to be used by the LLM.
    """

    locations: list[str]
    source_ids: list[str]
    content: str
    is_native_source: bool
    context: Context | None = None
    indices: list[Index] | None = None
    meta_ids: list[str] | None = None
    library_ids: list[str] | None = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()), init=False)

    def render_engram(self) -> str:
        """Generates a structured string representation of the engram, including its context and content.

        Returns:
            str: A formatted string containing the engram's context and text."""
        header = '<begin>'

        leading = '<location>\n'
        trailing = '</location>'

        location_str = leading + ('\n'.join(location for location in self.locations)) + trailing

        context_str = self.context.render_context() if self.context else ''

        leading = '<indices>\n'
        trailing = '\n</indices>'
        indices_str = (leading + ('\n'.join(index.text for index in self.indices)) + trailing) if self.indices else ''

        native_text = (
            'The text is directly from the source.'
            if self.is_native_source
            else 'The text is derived from one or more sources.'
        )

        content_str = f'<text>{self.content}</text>'
        footer = '</end>'

        ret_string = f'{header}\n{location_str}\n{context_str}\n{indices_str}\n{native_text}\n{content_str}\n{footer}\n'

        return ret_string
