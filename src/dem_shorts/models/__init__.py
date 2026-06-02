"""Frozen dataclass models for Dem-Shorts Studio.

See data-model.md for entity specifications.
"""

from src.dem_shorts.models.bias_report import BiasReport
from src.dem_shorts.models.gate_result import ComplianceGateResult
from src.dem_shorts.models.politician import Politician
from src.dem_shorts.models.shorts_draft import ShortsDraft
from src.dem_shorts.models.source_video import SourceVideo
from src.dem_shorts.models.speech_segment import SpeechSegment
from src.dem_shorts.models.uploaded_shorts import UploadedShorts
from src.dem_shorts.models.weekly_ranking import WeeklyRanking

__all__ = [
    "BiasReport",
    "ComplianceGateResult",
    "Politician",
    "ShortsDraft",
    "SourceVideo",
    "SpeechSegment",
    "UploadedShorts",
    "WeeklyRanking",
]
