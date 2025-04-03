# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

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

    id: str
    locations: list[str]
    source_ids: list[str]
    content: str
    is_native_source: bool
    context: dict[str, str] | None = None
    indices: list[Index] | None = None
    meta_ids: list[str] | None = None
    library_ids: list[str] | None = None
    accuracy: int | None = 0
    relevancy: int | None = 0
    created_date: datetime | None = None

    def generate_toml(self) -> str:
        def toml_escape(value: str) -> str:
            return f'"{value}"'

        def toml_list(values: list[str]) -> str:
            return '[' + ', '.join(toml_escape(v) for v in values) + ']'

        lines = [
            f'id = {toml_escape(self.id)}',
            f'content = {toml_escape(self.content)}',
            f'is_native_source = {str(self.is_native_source).lower()}',
            f'locations = {toml_list(self.locations)}',
            f'source_ids = {toml_list(self.source_ids)}',
        ]

        if self.meta_ids:
            lines.append(f'meta_ids = {toml_list(self.meta_ids)}')

        if self.library_ids:
            lines.append(f'library_ids = {toml_list(self.library_ids)}')

        if self.context:
            # Assuming context has a render_toml() method or can be represented as a dict
            inline = ', '.join(f'{k} = {toml_escape(v)}' for k, v in self.context.items())
            lines.append(f'context = {{ {inline} }}')

        if self.indices:
            # Flatten the index section
            for index in self.indices:
                # Assuming index has `text` and `embedding` attributes
                if index.text is None:
                    error = 'Null text in generate_toml.'
                    raise ValueError(error)

                lines.extend([
                    '[[indices]]',
                    f'text = {toml_escape(index.text)}',
                    f'embedding = {toml_escape(str(index.embedding))}',
                ])

        return '\n'.join(lines)

    def render(self) -> str:
        """
        Renders the engram into a structured string suitable for an LLM to use as context.
        """
        source_type = 'This data is an original source.' if self.is_native_source else ''

        meta_section = '<meta>\n'
        if self.locations:
            meta_section += 'Source: ' + ',\n    '.join(self.locations) + '\n'
        meta_section += '</meta>'

        context_section = ''
        if self.context:
            context_section = '<context>\n'
            context_section += '\n'.join(f'    {k}: {v}' for k, v in self.context.items()) + '\n'
            context_section += '</context>'

        content = '<content>'
        content += self.content.strip()
        content += '</content>'

        rendered = f'{source_type}\n\n' f'{meta_section}\n\n' f'{context_section}\n\n' f'{content}'

        return rendered
