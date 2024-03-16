import logging
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
LOGGING_LEVEL = logging.DEBUG
LOGGER = logging.getLogger("pyrefactorlsp")

handler = logging.StreamHandler()
handler.setLevel(LOGGING_LEVEL)
LOGGER.setLevel(LOGGING_LEVEL)
LOGGER.addHandler(handler)
