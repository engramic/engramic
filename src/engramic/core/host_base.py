import abc
from concurrent.futures import Future


class HostBase(abc.ABC):
    @abc.abstractmethod
    def run_task(self, coro) -> Future:
        """Runs an async task and returns a Future."""

    @abc.abstractmethod
    def run_tasks(self, coros) -> Future:
        """Runs multiple async tasks and returns a Future with the results."""

    @abc.abstractmethod
    def run_background(self, coro):
        """Runs an async task in the background."""
