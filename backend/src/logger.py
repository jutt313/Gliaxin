"""
Structured JSON logger for Gliaxin.

Cloud Run captures stdout and forwards to Cloud Logging automatically.
JSON-formatted logs are parsed as structured entries — searchable by
field, severity, and timestamp in the Cloud Console.

Usage:
    from logger import get_logger
    log = get_logger(__name__)
    log.info("memory processed", raw_id=raw_id, vault_id=vault_id)
"""

import json
import logging
import os
import sys
import traceback
from datetime import datetime, timezone


class _JsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON for Cloud Logging."""

    # Map Python log levels to Cloud Logging severity strings
    _SEVERITY = {
        logging.DEBUG:    "DEBUG",
        logging.INFO:     "INFO",
        logging.WARNING:  "WARNING",
        logging.ERROR:    "ERROR",
        logging.CRITICAL: "CRITICAL",
    }

    def format(self, record: logging.LogRecord) -> str:
        entry: dict = {
            "severity": self._SEVERITY.get(record.levelno, "DEFAULT"),
            "message":  record.getMessage(),
            "logger":   record.name,
            "time":     datetime.now(timezone.utc).isoformat(),
        }

        # Attach any extra kwargs passed to the log call
        for key, val in record.__dict__.items():
            if key not in (
                "name", "msg", "args", "levelname", "levelno", "pathname",
                "filename", "module", "exc_info", "exc_text", "stack_info",
                "lineno", "funcName", "created", "msecs", "relativeCreated",
                "thread", "threadName", "processName", "process", "message",
                "taskName",
            ):
                entry[key] = val

        if record.exc_info:
            entry["exception"] = "".join(traceback.format_exception(*record.exc_info))

        return json.dumps(entry, default=str)


class _StructuredLogger:
    def __init__(self, logger: logging.Logger):
        self._logger = logger

    def _emit(self, level: int, message: str, **fields) -> None:
        exc_info = fields.pop("exc_info", None)
        self._logger.log(level, message, extra=fields, exc_info=exc_info)

    def debug(self, message: str, **fields) -> None:
        self._emit(logging.DEBUG, message, **fields)

    def info(self, message: str, **fields) -> None:
        self._emit(logging.INFO, message, **fields)

    def warning(self, message: str, **fields) -> None:
        self._emit(logging.WARNING, message, **fields)

    def error(self, message: str, **fields) -> None:
        self._emit(logging.ERROR, message, **fields)

    def exception(self, message: str, **fields) -> None:
        fields["exc_info"] = True
        self._emit(logging.ERROR, message, **fields)


def _build_logger(name: str) -> _StructuredLogger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        formatter = _JsonFormatter()

        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setFormatter(formatter)
        logger.addHandler(stdout_handler)

        log_file = os.getenv("LOG_FILE")
        if log_file:
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        logger.propagate = False

        level_name = os.getenv("LOG_LEVEL", "INFO").upper()
        logger.setLevel(getattr(logging, level_name, logging.INFO))

    return _StructuredLogger(logger)


def get_logger(name: str) -> _StructuredLogger:
    return _build_logger(name)
