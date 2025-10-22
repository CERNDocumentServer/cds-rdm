from contextlib import contextmanager

from flask import current_app


class Logger:

    def __init__(self, inspire_id, record_pid=None):
        self.inspire_id = inspire_id
        self.record_pid = record_pid

    def _prefix(self):
        parts = []
        if self.inspire_id:
            parts.append(f"INSPIRE#{self.inspire_id}")
        if self.record_pid:
            parts.append(f"CDS#{self.record_pid}")
        return "[" + " ".join(parts) + "] " if parts else ""

    def info(self, message):
        current_app.logger.info(self._prefix() + message)

    def debug(self, message):
        current_app.logger.debug(self._prefix() + message)

    def warning(self, message):
        current_app.logger.warning(self._prefix() + message)

    def error(self, message):
        current_app.logger.error(self._prefix() + message)


def hlog(func):
    """Simple decorator that logs before and after calling the method."""

    def wrapper(self, stream_entry, *args, record_pid=None, **kwargs):

        inspire_id = stream_entry.entry["id"]
        logger = Logger(inspire_id=inspire_id, record_pid=record_pid)
        current_app.logger.debug("Call: {}".format(func.__name__))

        result = func(
            self,
            stream_entry,
            *args,
            inspire_id=inspire_id,
            record_pid=record_pid,
            logger=logger,
            **kwargs,
        )

        current_app.logger.debug("Return: {}".format(func.__name__))
        return result

    return wrapper
