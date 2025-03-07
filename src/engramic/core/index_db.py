from abc import ABC, abstractmethod

from index import Index


class IndexDB(ABC):
    @abstractmethod
    def query(self) -> list[Index]:
        pass
