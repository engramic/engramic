# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engramic.core.index import Index


@dataclass()
class Meta:
    """
    Test.
    """

    id: str
    locations: list[str]
    source_ids: list[str]
    keywords: list[str]
    summary_initial: str | None = None
    summary_full: Index | None = None

    def render(self) -> str:
        def toml_escape(value: str) -> str:
            return f'"{value}"'

        def toml_list(values: list[str]) -> str:
            return f"[{', '.join(toml_escape(v) for v in values)}]"

        output = ['[meta]']
        data = asdict(self)
        for key, value in data.items():
            if isinstance(value, list):
                output.append(f'{key} = {toml_list(value)}')
            elif value is None:
                continue  # skip None values
            else:
                output.append(f'{key} = {toml_escape(value)}')
        return '\n'.join(output)
