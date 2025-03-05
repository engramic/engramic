# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from dataclasses import dataclass

import Generic
import List
import TypeVar

T = TypeVar('T')  # Declare a type variable


@dataclass(frozen=True)
class Index(Generic[T]):
    embedding: List[T]
    text: str
