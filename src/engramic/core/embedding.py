from dataclasses import dataclass
from typing import list


@dataclass(frozen=True)
class Index:
    embedding: list[float]
    text: str
