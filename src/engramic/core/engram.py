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
    Represents a unit of memory, consisting of a text string (e.g., a phrase, sentence, or paragraph)
    along with contextual information that helps in retrieval and responses.

    Attributes:
        id (str): A unique identifier for the engram.
        locations (list[str]): One or more locations where the engram was generated such as file paths or URLs.
        source_ids (list[str]): One or more identifiers linking the engram to its originating sources.
        content (str): The textual content of the engram.
        is_native_source (bool): Whether the content is directly extracted from a source (True) or derived/generated (False).
        context (dict[str, str] | None): Optional key-value pairs providing additional context for the engram.
        indices (list[Index] | None): Optional list of semantic indices associated with the engram, typically used for embedding-based search.
        meta_ids (list[str] | None): Optional metadata identifiers associated with this Engram.
        library_ids (list[str] | None): Optional identifiers grouping this engram into document collections or libraries.
        accuracy (int | None): An optional accuracy score assigned to the engram by validation on the Codify Service).
        relevancy (int | None): An optional relevancy score assigned to the engram by validation on the Codify Service).
        created_date (datetime | None): The creation timestamp of the engram.

    Methods:
        generate_toml() -> str:
            Serializes the engram to a TOML-formatted string, including all non-null attributes and flattening indices.
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
