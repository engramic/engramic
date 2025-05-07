# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engramic.core.index import Index


@dataclass()
class Engram:
    """
    Represents a unit of memory that encapsulates a text fragment with rich metadata
    for semantic indexing and contextual relevance.

    Attributes:
        id (str): Unique identifier for the engram.
        locations (list[str]): One or more file paths, URLs, or other locations associated with the engram.
        source_ids (list[str]): Identifiers of the original source documents from which the engram was derived.
        content (str): The main textual content of the engram.
        is_native_source (bool): Indicates if the content was directly extracted (True) or generated (False).
        context (dict[str, str] | None): Optional contextual metadata in key-value format to enhance retrieval or classification.
        indices (list[Index] | None): Optional semantic indices, typically for vector-based retrieval.
        meta_ids (list[str] | None): Optional list of metadata tags or identifiers relevant to the engram.
        library_ids (list[str] | None): Optional identifiers linking this engram to document groups or libraries.
        accuracy (int | None): Optional accuracy score assigned during validation (e.g., via Codify Service).
        relevancy (int | None): Optional relevancy score assigned during validation (e.g., via Codify Service).
        created_date (int | None): Optional Unix timestamp representing the creation time of the engram.

    Methods:
        generate_toml() -> str:
            Serializes the engram into a TOML-formatted string, including non-null fields.
            Nested indices are flattened, and context is rendered as an inline TOML table.
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
    created_date: int | None = None

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
