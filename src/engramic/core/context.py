from abc import ABC, abstractmethod


class Context(ABC):
    def __init__(self, context_dict: dict):
        self.context_dict = context_dict

    @abstractmethod
    def render_context(self) -> str:
        """Abstract method that must be implemented by subclasses to render context meaningfully."""
