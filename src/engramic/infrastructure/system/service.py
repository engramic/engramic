# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from concurrent.futures import Future
import asyncio
import logging
import threading



class Service:
    """Base class for services running in their own thread with an asyncio loop."""

    def __init__(self)->None:
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        """Start the service thread."""
        self.thread.start()

    def _run(self)->None:
        """Run the event loop in a separate thread."""
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def stop(self)->None:
        """Stop the event loop and wait for the thread to exit."""
        self.loop.call_soon_threadsafe(self.loop.stop())
        self.thread.join()

    def submit_async_task(self, coro)->Future:
        """Submit an asyncio coroutine and ensure exceptions are logged."""
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)

        def handle_exception(fut: asyncio.Future) -> None:
            try:
                fut.result()
            except asyncio.TimeoutError as e:
                logging.warning('Async task timed out: %s', e)
            except RuntimeError:
                logging.exception('Runtime error in async task.')
            except Exception:
                logging.exception('Unexpected exception in async task')
            except BaseException:
                logging.critical('Critical system exception')
                raise

        future.add_done_callback(handle_exception)
        return future
