# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any


class DB(ABC):
    """
    An abstract base class that defines an interface for any database. This de
    """

    class DBTables(Enum):
        ENGRAM = 'engram'
        META = 'meta'
        OBSERVATION = 'observation'
        HISTORY = 'history'

    @abstractmethod
    def connect(self, args: dict[str, Any]) -> None:
        """Establish a connection to the database."""
        # or `return False`

    @abstractmethod
    def close(self, args: dict[str, Any]) -> None:
        """Close the connection to the database."""
        # or `return False`

    @abstractmethod
    def fetch(self, table: DBTables, ids: list[str], args: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
        """Execute a query without additional data."""
        # or `return None`

    @abstractmethod
    def insert_documents(self, table: DBTables, docs: list[dict[str, Any]], args: dict[str, Any]) -> None:
        """Execute a query with additional data."""
        # or `return None`
