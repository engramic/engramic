# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.
import asyncio
import logging
import threading
import time
from collections.abc import Awaitable, Sequence
from concurrent.futures import Future
from threading import Thread
from typing import Any

from engramic.core.host_base import HostBase
from engramic.infrastructure.system.plugin_manager import PluginManager
from engramic.infrastructure.system.service import Service


class Host(HostBase):
    def __init__(self, selected_profile: str, services: list[type[Service]], *, ignore_profile: bool = False) -> None:
        self.plugin_manager: PluginManager = PluginManager(selected_profile, ignore_profile=ignore_profile)

        self.services: dict[str, Service] = {}
        for ctr in services:
            self.services[ctr.__name__] = ctr(self)  # Instantiate the class

        self.async_loop_event = threading.Event()

        self.thread = Thread(target=self._start_async_loop, daemon=True, name='Async Thread')
        self.thread.start()
        time.sleep(1)  # OK, this isn't pretty but it works. Need to fix.

        self.stop_event: threading.Event = threading.Event()

        for ctr in services:
            self.services[ctr.__name__].start()

    def _start_async_loop(self) -> None:
        """Run the event loop in a separate thread."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.call_soon_threadsafe(self._init_services_async)
        try:
            self.loop.run_forever()
        except Exception:
            logging.exception('Unhandled exception in async event loop')

    def _init_services_async(self) -> None:
        if 'MessageService' in self.services:
            self.services['MessageService'].init_async()

        for name in self.services:
            if name == 'MessageService':
                continue
            self.services[name].init_async()

    def run_task(self, coro: Awaitable[None]) -> Future[Any]:
        """Runs an async task and returns a Future that can be awaited later."""
        if not asyncio.iscoroutine(coro):
            error = 'Expected a single coroutine. Add () to the coroutines when you add them to run_task (e.g. my_func() not my_func ). Must be async.'
            raise TypeError(error)

        future = asyncio.run_coroutine_threadsafe(coro, self.loop)

        # Ensure exceptions are logged
        def handle_future_exception(f: Future[None]) -> None:
            exc = f.exception()  # Fetch exception, if any
            if exc:
                logging.exception('Unhandled exception in run_task(): FUNCTION: %s, ERROR: %s', {coro.__name__}, {exc})

        future.add_done_callback(handle_future_exception)  # Attach exception handler
        return future

    def run_tasks(self, coros: Sequence[Awaitable[Any]]) -> Future[dict[str, Any]]:
        """Runs multiple async tasks simultaneously and returns a Future with the results."""
        if not all(asyncio.iscoroutine(c) for c in coros):
            error = 'Expected a list of coroutines. Add () to the coroutines when you add them to run_tasks (e.g. my_func() not my_func ). Must be async.'
            raise TypeError(error)

        async def gather_tasks() -> dict[str, Any]:
            try:
                gather = await asyncio.gather(*coros, return_exceptions=True)
                ret: dict[str, Any] = {}
                for i, coro in enumerate(coros):
                    name = self._get_coro_name(coro)
                    if name in ret:
                        if isinstance(ret[name], list):
                            ret[name].append(gather[i])
                        else:
                            ret[name] = [ret[name], gather[i]]
                    else:
                        ret[name] = gather[i]
            except Exception:
                logging.exception('Unexpected error in gather_tasks()')
                raise
            else:
                return ret

        future = asyncio.run_coroutine_threadsafe(gather_tasks(), self.loop)

        # Handle future exceptions to avoid swallowing errors
        def handle_future_exception(f: Future[dict[str, Any]]) -> None:
            exc = f.exception()
            if exc:
                logging.exception('Unhandled exception in run_tasks():  ERROR: %s', {exc})

        future.add_done_callback(handle_future_exception)

        return future

    def run_background(self, coro: Awaitable[None]) -> None:
        """Runs an async task in the background without waiting for its result."""
        if not asyncio.iscoroutine(coro):
            error = 'Expected a coroutine'
            raise TypeError(error)
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)

        # Ensure background exceptions are logged
        def handle_future_exception(f: Future[None]) -> None:
            exc = f.exception()
            if exc:
                logging.exception(
                    'Unhandled exception in run_background(): FUNCTION: %s, ERROR: %s', {coro.__name__}, {exc}
                )

        future.add_done_callback(handle_future_exception)

    def get_service(self, cls_in: type[Service]) -> Service:
        name = cls_in.__name__
        if name in self.services and self.services[name].validate_service():
            return self.services[name]
        error = 'Service not found in get_service.'
        raise RuntimeError(error)

    def shutdown(self) -> None:
        """Stop all running services."""
        for service in self.services:
            self.services[service].stop()

        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join()

        # host ready for shutdown
        self.stop_event.set()

    def wait_for_shutdown(self) -> None:
        try:
            self.stop_event.wait()

        except KeyboardInterrupt:
            self.shutdown()
            logging.info('\nShutdown requested. Exiting gracefully...')
        finally:
            logging.info('Cleaning up.')

    def _get_coro_name(self, coro: Awaitable[None]) -> str:
        """Extracts the coroutine function name if possible, otherwise generates a fallback name."""
        try:
            if hasattr(coro, '__name__'):  # Works for direct functions
                return str(coro.__name__)
            if hasattr(coro, 'cr_code') and hasattr(coro.cr_code, 'co_name'):  # Works for coroutine objects
                return str(coro.cr_code.co_name)
        except AttributeError:  # More specific exception
            logging.warning('Failed to retrieve coroutine name due to missing attributes.')
        except TypeError:  # If `coro` isn't the expected type
            logging.warning('Failed to retrieve coroutine name due to incorrect type.')

        return 'unknown_coroutine'
