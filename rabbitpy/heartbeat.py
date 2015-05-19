"""

"""
import logging
import threading
import time

from rabbitpy import exceptions

LOGGER = logging.getLogger(__name__)


class Checker(object):

    MAX_MISSED_HEARTBEATS = 2

    def __init__(self, io, exception_queue):
        self._exceptions = exception_queue
        self._io = io
        self._interval = 0
        self._last_bytes = 0
        self._last_heartbeat = 0
        self._lock = threading.Lock()

    def on_heartbeat(self):
        LOGGER.debug('Heartbeat received, updating the last_heartbeat time')
        self._lock.acquire(True)
        self._last_heartbeat = time.time()
        self._lock.release()

    def start(self, interval):
        self._interval = interval
        if self._interval:
            self._start_heartbeat_timer()

    def _check_for_heartbeat(self):

        # If the byte count has incremented no need to check time
        if self._io.bytes_received > self._last_bytes:
            LOGGER.debug('Data has been received, exiting heartbeat check')
            self._lock.acquire(True)
            self._last_bytes = self._io.bytes_received
            self._lock.release()
            self._start_heartbeat_timer()
            return

        age = time.time() - self._last_heartbeat
        threshold = self._interval * self.MAX_MISSED_HEARTBEATS
        LOGGER.debug('Checking for heartbeat, last: %i sec ago, threshold: %i',
                     age, threshold)
        if age >= threshold:
            LOGGER.error('Have not received a heartbeat in %i seconds', age)
            message = 'No heartbeat in {0} seconds'.format(age)
            self._exceptions.put(exceptions.ConnectionResetException(message))
        else:
            self._start_heartbeat_timer()

    def _start_heartbeat_timer(self):
        """Create and start the timer that will check every N*2 seconds to
        ensure that a heartbeat has been requested.

        """
        LOGGER.debug('Started a heartbeat timer that will fire in %i sec',
                     self._interval)
        self._heartbeat_timer = threading.Timer(self._interval,
                                                self._check_for_heartbeat)
        self._heartbeat_timer.start()
