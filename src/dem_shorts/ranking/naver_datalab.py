"""T109: 네이버 데이터랩 공공 API 기반 검색 트렌드.

공식 공공 API: https://openapi.naver.com/v1/datalab/search
- `NAVER_DATALAB_CLIENT_ID` / `NAVER_DATALAB_CLIENT_SECRET` 필요
- 하루 1,000회 무료 호출 제공

미설정 시 0.0 반환.
"""
from __future__ import annotations

import json
import logging
import os
import urllib.request
from datetime import date, timedelta
from typing import Iterable

logger = logging.getLogger(__name__)

_API_URL = "https://openapi.naver.com/v1/datalab/search"
_WINDOW_DAYS = 7
_REQUEST_TIMEOUT_SEC = 15


def _credentials() -> tuple[str, str] | None:
    cid = os.getenv("NAVER_DATALAB_CLIENT_ID", "")
    csec = os.getenv("NAVER_DATALAB_CLIENT_SECRET", "")
    if cid and csec:
        return cid, csec
    return None


def _fetch_trend(name: str, creds: tuple[str, str]) -> float:
    """네이버 데이터랩 검색 트렌드 평균 (0~100)."""
    today = date.today()
    start = today - timedelta(days=_WINDOW_DAYS)
    body = {
        "startDate": start.isoformat(),
        "endDate": today.isoformat(),
        "timeUnit": "date",
        "keywordGroups": [{"groupName": name, "keywords": [name]}],
    }
    req = urllib.request.Request(
        _API_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "X-Naver-Client-Id": creds[0],
            "X-Naver-Client-Secret": creds[1],
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT_SEC) as resp:
            data = json.loads(resp.read())
    except Exception as exc:
        logger.warning("naver_datalab fetch failed for %s: %s", name, exc)
        return 0.0
    results = data.get("results", [])
    if not results:
        return 0.0
    points = results[0].get("data", [])
    if not points:
        return 0.0
    return float(sum(p.get("ratio", 0) for p in points) / len(points))


def fetch_scores(names: Iterable[str]) -> dict[str, float]:
    creds = _credentials()
    if creds is None:
        return {n: 0.0 for n in names}
    return {name: _fetch_trend(name, creds) for name in names}
