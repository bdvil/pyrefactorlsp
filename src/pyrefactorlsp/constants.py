import logging
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
LOGGING_LEVEL = logging.DEBUG
LOGGER = logging.getLogger("pyrefactorlsp")

handler = logging.FileHandler(PROJECT_DIR / "pyrefactorlsp.log")
handler.setLevel(LOGGING_LEVEL)
LOGGER.setLevel(LOGGING_LEVEL)
LOGGER.addHandler(handler)

stream_handler = logging.StreamHandler()
stream_handler.setLevel(LOGGING_LEVEL)
LOGGER.addHandler(stream_handler)


__all__ = [
    "PROJECT_DIR",
    "LOGGING_LEVEL",
    "LOGGER",
]
