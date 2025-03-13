# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.
import asyncio
import logging
import threading
from concurrent.futures import Future
from threading import Thread

from engramic.infrastructure.system.plugin_manager import PluginManager
from engramic.infrastructure.system.service import Service


class Host:
    def __init__(self, selected_profile: str, services: list[type[Service]]) -> None:
        self.plugin_manager: PluginManager = PluginManager(selected_profile)

        self.services: dict[str, Service] = {}

        for ctr in services:
            self.services[ctr.__name__] = ctr(self.plugin_manager, self)  # Instantiate the class

        self.async_loop_event = threading.Event()
        self.thread = Thread(target=self._start_async_loop, daemon=True, name='Async Loop')
        self.thread.start()
        self.async_loop_event.wait()  # wait for async init to complete.

        self.stop_event: threading.Event = threading.Event()

    def _start_async_loop(self):
        """Run the event loop in a separate thread."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.call_soon_threadsafe(self._init_services_async)
        self.loop.call_soon_threadsafe(self.async_loop_event.set)
        try:
            self.loop.run_forever()
        except RuntimeError:
            logging.exception('Runtime error on async loop.')

    def _init_services_async(
        self,
    ):
        if 'MessageService' in self.services:
            self.services['MessageService'].init_async()

        for name in self.services:
            if name == 'MessageService':
                continue
            self.services[name].init_async()

    def run_task(self, coro) -> Future:
        """Runs an async task and returns a Future that can be awaited later."""
        if not asyncio.iscoroutine(coro):
            error = 'Expected a coroutine'
            raise TypeError(error)
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    def run_tasks(self, coros) -> Future:
        """Runs multiple async tasks simultaneously and returns a Future with the results."""
        if not all(asyncio.iscoroutine(c) for c in coros):
            error = 'Expected a list of coroutines'
            raise TypeError(error)

        async def gather_tasks():
            gather = await asyncio.gather(*coros)
            coros_with_names = {self._get_coro_name(coro): coro for coro in coros}
            ret = {}
            for i, name in enumerate(coros_with_names):
                ret[name] = gather[i]
            return ret

        return asyncio.run_coroutine_threadsafe(gather_tasks(), self.loop)

    def run_background(self, coro):
        """Runs an async task in the background without waiting for its result."""
        if not asyncio.iscoroutine(coro):
            error = 'Expected a coroutine'
            raise TypeError(error)
        asyncio.run_coroutine_threadsafe(coro, self.loop)

    def get_service(self, cls_in: type[Service]) -> Service:
        name = cls_in.__name__
        if name in self.services and self.services[name].validate():
            return self.services[name]
        return None

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

    def _get_coro_name(self, coro):
        """Extracts the coroutine function name if possible, otherwise generates a fallback name."""
        try:
            if hasattr(coro, '__name__'):  # Works for direct functions
                return coro.__name__
            if hasattr(coro, 'cr_code') and hasattr(coro.cr_code, 'co_name'):  # Works for coroutine objects
                return coro.cr_code.co_name
        except AttributeError:  # More specific exception
            logging.warning('Failed to retrieve coroutine name due to missing attributes.')
        except TypeError:  # If `coro` isn't the expected type
            logging.warning('Failed to retrieve coroutine name due to incorrect type.')

        return 'unknown_coroutine'
