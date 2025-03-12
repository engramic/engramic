# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import asyncio
import logging
import threading
from concurrent.futures import Future


class Service:
    """Base class for services running in their own thread with an asyncio loop."""

    def __init__(self) -> None:
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def start(self, host) -> None:
        self.host = host
        """Start the service thread."""
        self.thread.start()

    def _run(self) -> None:
        """Run the event loop in a separate thread."""
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    async def _shutdown_loop(self):
        tasks = [t for t in asyncio.all_tasks(self.loop) if t is not asyncio.current_task()]
        [task.cancel() for task in tasks]
        await asyncio.gather(*tasks, return_exceptions=True)
        self.loop.stop()

    def stop(self) -> None:
        self.loop.call_soon_threadsafe(asyncio.create_task, self._shutdown_loop())
        self.thread.join()

    @staticmethod
    async def sleep(seconds) -> None:
        await asyncio.sleep(seconds)

    def submit_async_tasks(self, *coros) -> Future:
        """
        Submit multiple asyncio coroutines and return a single future
        that resolves to a dictionary mapping coroutine names to results.

        Example:
        future = scheduler.submit_async_tasks(coro1(), coro2())
        """
        coros_with_names = {self._get_coro_name(coro): coro for coro in coros}
        future = asyncio.run_coroutine_threadsafe(self._run_tasks(coros_with_names), self.loop)

        def handle_exception(fut: Future) -> None:
            try:
                fut.result()  # Ensures exceptions are logged
            except asyncio.TimeoutError as e:
                logging.warning('Async tasks timed out: %s', e)
            except RuntimeError:
                logging.exception('Runtime error in async tasks.')
            except Exception:
                logging.exception('Unexpected exception in async tasks')
            except BaseException:
                logging.critical('Critical system exception')
                raise

        future.add_done_callback(handle_exception)
        return future

    async def _run_tasks(self, coros_with_names):
        """Runs multiple coroutines concurrently and returns results with names."""
        tasks = {name: asyncio.create_task(coro) for name, coro in coros_with_names.items()}
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        for name, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                logging.error('Task %s failed with error: %s', name, result)

        return dict(zip(tasks.keys(), results))

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
