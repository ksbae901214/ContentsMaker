"""V3 격리 로거 — root 로거 propagation 없음, 독립 핸들러.

기존 V1/V2 로깅 설정과 충돌 방지.
"""
from __future__ import annotations

import logging
import sys
from typing import Final

_LOGGER_NAME: Final[str] = "jpolitics"
_FORMAT: Final[str] = "[jpolitics:%(name)s] %(levelname)s %(message)s"

_configured = False


def get_logger(name: str = "") -> logging.Logger:
    """Return jpolitics-scoped logger. Sub-modules pass their own name suffix.

    Examples:
        get_logger("planner")  → "jpolitics.planner"
        get_logger()           → "jpolitics"
    """
    global _configured
    if not _configured:
        root = logging.getLogger(_LOGGER_NAME)
        root.setLevel(logging.INFO)
        root.propagate = False  # root 로거로 흘러가지 않음 (격리)
        if not root.handlers:
            handler = logging.StreamHandler(sys.stderr)
            handler.setFormatter(logging.Formatter(_FORMAT))
            root.addHandler(handler)
        _configured = True
    if name:
        return logging.getLogger(f"{_LOGGER_NAME}.{name}")
    return logging.getLogger(_LOGGER_NAME)
