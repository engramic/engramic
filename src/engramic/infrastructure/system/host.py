# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import logging
import threading


class Host:
    def __init__(self, service_classes)->None:
        """Initialize the host with an empty service list."""
        self.services = [service_class() for service_class in service_classes]
        for service in self.services:
            service.start()
        self.stop_event = threading.Event()

    def stop_all(self)->None:
        """Stop all running services."""
        for service in self.services:
            service.stop()

    def wait_for_shutdown(self)->None:
        try:
            self.stop_event.wait()  # This blocks until the event is set
        except KeyboardInterrupt:
            logging.info("\nShutdown requested. Exiting gracefully...")
        finally:
            self.cleanup()

    def cleanup(self)->None:
        logging.info("Cleaning up.")
