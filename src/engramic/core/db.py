# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from abc import ABC, abstractmethod
from typing import Any


class DB(ABC):
    """
    An abstract base class that defines an interface for any Large Language Model.
    """

    @abstractmethod
    def connect(self, **kwargs: Any) -> bool:
        pass
    
    def close(self)->bool:
        pass

    def execute(self, **kwargs: Any):
        pass
