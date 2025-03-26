import abc
from collections.abc import Awaitable, Sequence
from concurrent.futures import Future
from typing import Any


class Host(abc.ABC):
    @abc.abstractmethod
    def run_task(self, coro: Awaitable[Any]) -> Future[Any]:
        """Runs an async task and returns a Future."""

    @abc.abstractmethod
    def run_tasks(self, coros: Sequence[Awaitable[Any]]) -> Future[dict[str, Any]]:
        """Runs multiple async tasks and returns a Future with the results."""

    @abc.abstractmethod
    def run_background(self, coro: Awaitable[Any]) -> None:
        """Runs an async task in the background."""
