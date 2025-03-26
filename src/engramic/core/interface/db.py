# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from abc import ABC, abstractmethod
from typing import Any


class DB(ABC):
    """
    An abstract base class that defines an interface for any database. This de
    """

    @abstractmethod
    def connect(self) -> None:
        """Establish a connection to the database."""
        # or `return False`

    @abstractmethod
    def close(self) -> None:
        """Close the connection to the database."""
        # or `return False`

    @abstractmethod
    def execute(self, query: str) -> dict[str, Any]:
        """Execute a query without additional data."""
        # or `return None`

    @abstractmethod
    def execute_data(self, query: str, data: dict[str, Any]) -> None:
        """Execute a query with additional data."""
        # or `return None`
