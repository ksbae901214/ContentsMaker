"""V3 독립 로거 — 루트 로거로 전파하지 않음 (격리 원칙)."""
import logging
import sys

logger = logging.getLogger("jpolitics")
logger.propagate = False

if not logger.handlers:
    _handler = logging.StreamHandler(sys.stderr)
    _handler.setFormatter(
        logging.Formatter("%(asctime)s [V3:%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    )
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)
