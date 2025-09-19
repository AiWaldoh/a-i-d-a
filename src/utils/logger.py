import logging
import logging.handlers
import time
import os
import sys
from pathlib import Path

def setup_logging(
    *,
    to_file: bool = True,
    log_file: str = "logs/app.log",
    console_level: str | None = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> None:
    """
    Simple, performant logging setup.
    - Idempotent (safe to call many times)
    - Rotating file logs (default on) to "logs/app.log"
    - Minimal console logs; level configurable via LOG_LEVEL_CONSOLE
    - UTC ISO8601 timestamps with trailing 'Z'
    - Logs uncaught exceptions once
    """
    # Respect env toggles but keep API simple
    if console_level is None:
        console_level = os.getenv("LOG_LEVEL_CONSOLE", "WARNING")
    to_file = bool(int(os.getenv("LOG_TO_FILE", "1"))) if to_file is True else to_file

    root = logging.getLogger()
    if getattr(root, "_configured", False):
        return  # already configured

    root.setLevel(logging.DEBUG)  # capture everything; handlers decide what to emit

    # Console handler (always on)
    console = logging.StreamHandler()
    console.setLevel(getattr(logging, console_level.upper(), logging.WARNING))
    console.setFormatter(logging.Formatter(
        "%(levelname)s: %(message)s"
    ))

    handlers = [console]

    # Optional rotating file handler
    if to_file:
        Path(Path(log_file).parent).mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
        )
        file_formatter = logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s %(filename)s:%(lineno)d %(funcName)s - %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%SZ",
        )
        file_formatter.converter = time.gmtime  # UTC
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.DEBUG)
        handlers.append(file_handler)

    for h in handlers:
        root.addHandler(h)

    # Log uncaught exceptions with traceback once
    def _excepthook(exc_type, exc, tb):
        logging.getLogger(__name__).exception("Uncaught exception", exc_info=(exc_type, exc, tb))
    sys.excepthook = _excepthook

    root._configured = True
