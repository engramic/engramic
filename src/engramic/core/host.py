# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.
from __future__ import annotations

import asyncio
import inspect
import json
import logging
import os
import queue
import threading
import time
from threading import Thread
from typing import TYPE_CHECKING, Any

from engramic.core.index import Index
from engramic.infrastructure.system.plugin_manager import PluginManager

if TYPE_CHECKING:
    from collections.abc import Awaitable, Sequence
    from concurrent.futures import Future

    from engramic.infrastructure.system.service import Service


class Host:
    def __init__(
        self,
        selected_profile: str,
        services: list[type[Service]],
        *,
        ignore_profile: bool = False,
        generate_mock_data: bool = False,
    ) -> None:
        del ignore_profile

        path = '.env'
        if os.path.exists(path):
            with open(path, encoding='utf-8') as f:
                for line in f:
                    if line.strip() and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        os.environ[key] = value

        self.mock_data_collector: dict[str, dict[str, Any]] = {}
        self.is_mock_profile = selected_profile == 'mock'
        self.generate_mock_data = generate_mock_data

        self.exception_queue: queue.Queue[Any] = queue.Queue()

        if self.is_mock_profile:
            self.read_mock_data()

        self.plugin_manager: PluginManager = PluginManager(self, selected_profile)

        self.services: dict[str, Service] = {}
        for ctr in services:
            self.services[ctr.__name__] = ctr(self)  # Instantiate the class

        self.init_async_done_event = threading.Event()

        self.thread = Thread(target=self._start_async_loop, daemon=True, name='Async Thread')
        self.thread.start()
        self.init_async_done_event.wait()

        self.stop_event: threading.Event = threading.Event()
        self.shutdown_message_recieved = False

        for ctr in services:
            self.services[ctr.__name__].start()

    def _start_async_loop(self) -> None:
        """Run the event loop in a separate thread."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        future = asyncio.run_coroutine_threadsafe(self._init_services_async(), self.loop)

        def on_done(_fut: Future[None]) -> None:
            # If there's an error, log it; either way, we set the event
            exc = _fut.exception()
            if exc:
                logging.exception('Unhandled exception during init_services_async: %s', exc)
            else:
                self.init_async_done_event.set()

        future.add_done_callback(on_done)

        try:
            self.loop.run_forever()
        except Exception:
            logging.exception('Unhandled exception in async event loop')

    async def _init_services_async(self) -> None:
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
                    if name not in ret:
                        ret[name] = []
                    ret[name].append(gather[i])
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
                self.exception_queue.put(f)

        future.add_done_callback(handle_future_exception)

        return future

    def run_background(self, coro: Awaitable[None]) -> Future[None]:
        """Runs an async task in the background without waiting for its result."""
        if not asyncio.iscoroutine(coro):
            error = 'Expected a coroutine'
            raise TypeError(error)
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)

        # Ensure background exceptions are logged
        def handle_future_exception(f: Future[None]) -> None:
            if f.cancelled():
                logging.debug('Future was cancelled')
                return

            exc = f.exception()
            if exc:
                logging.exception(
                    'Unhandled exception in run_background(): FUNCTION: %s, ERROR: %s', {coro.__name__}, {exc}
                )
                self.exception_queue.put(f)

        future.add_done_callback(handle_future_exception)
        return future

    def get_service(self, cls_in: type[Service]) -> Service:
        name = cls_in.__name__
        if name in self.services and self.services[name].validate_service():
            return self.services[name]
        error = 'Service not found in get_service.'
        raise RuntimeError(error)

    def trigger_shutdown(self) -> None:
        self.shutdown_message_recieved = True
        self.stop_event.set()

    def shutdown(self) -> None:
        self.shutdown_message_recieved = True
        """Stop all running services."""
        for service in self.services:
            self.services[service].stop()

        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join()

        if not self.exception_queue.empty():
            exc = self.exception_queue.get().exception()
            error = f'Background thread failed: {exc}'
            raise RuntimeError(error) from None

    def wait_for_shutdown(self, timeout: float | None = None) -> None:
        try:
            if not self.shutdown_message_recieved:
                self.stop_event.wait(timeout)
            time.sleep(1)
            self.shutdown()

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

    def update_mock_data_input(self, service: Service, value: dict[str, Any]) -> None:
        if self.generate_mock_data:
            service_name = service.__class__.__name__
            concat = f'{service_name}-input'

            if self.mock_data_collector.get(concat) is not None:
                error = 'Mock data collection collision error. Missing an index?'
                raise ValueError(error)

            self.mock_data_collector[concat] = value

    def update_mock_data_output(self, service: Service, value: dict[str, Any]) -> None:
        if self.generate_mock_data:
            service_name = service.__class__.__name__
            concat = f'{service_name}-output'

            if self.mock_data_collector.get(concat) is not None:
                error = 'Mock data collection collision error. Missing an index?'
                raise ValueError(error)

            self.mock_data_collector[concat] = value

    def update_mock_data(self, plugin: dict[str, Any], response: list[dict[str, Any]], index_in: int = 0) -> None:
        if self.generate_mock_data:
            caller_name = inspect.stack()[1].function
            usage = plugin['usage']
            index = index_in

            concat = f'{caller_name}-{usage}-{index}'

            if self.mock_data_collector.get(concat) is not None:
                error = 'Mock data collection collision error. Missing an index?'
                raise ValueError(error)

            save_string = response[0]
            self.mock_data_collector[concat] = save_string

    class CustomEncoder(json.JSONEncoder):
        def default(self, obj: Any) -> Any:
            if isinstance(obj, set):
                return {'__type__': 'set', 'value': list(obj)}
            if isinstance(obj, Index):
                return {'__type__': 'Index', 'value': {'text': obj.text, 'embedding': obj.embedding}}

            return super().default(obj)

    def custom_decoder(self, obj: Any) -> Any:
        if '__type__' in obj:
            type_name = obj['__type__']
            if type_name == 'set':
                return set(obj['value'])
            if type_name == 'Index':
                return Index(**obj['value'])
        return obj

    def write_mock_data(self) -> None:
        if self.generate_mock_data:
            directory = 'local_storage/mock_data'
            filename = 'mock.txt'
            full_path = os.path.join(directory, filename)

            # Create the directory if it doesn't exist
            os.makedirs(directory, exist_ok=True)

            output = json.dumps(self.mock_data_collector, cls=self.CustomEncoder, indent=1)

            # Write to the file (this will overwrite if it exists)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(output)
                f.flush()

    def read_mock_data(self) -> None:
        directory = 'tests/data'
        filename = 'mock.txt'
        full_path = os.path.join(directory, filename)

        with open(full_path, encoding='utf-8') as f:
            data_in = f.read()
            self.mock_data_collector = json.loads(data_in, object_hook=self.custom_decoder)

    def mock_update_args(self, plugin: dict[str, Any], index_in: int = 0) -> dict[str, Any]:
        args: dict[str, Any] = plugin['args']

        if self.is_mock_profile:
            caller_name = inspect.stack()[1].function
            usage = plugin['usage']
            concat = f'{caller_name}-{usage}-{index_in}'
            args.update({'mock_lookup': concat})

        return args
