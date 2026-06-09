"""E3 — 정치인 카드 (인물 사진 + 정당 + 정당 컬러 + 데이터).

vs_card / grid_2x2 / data_card 레이아웃 씬의 comparison_cards 원소.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PoliticianCard:
    name: str
    party: str
    party_color: str  # 헥스 #RRGGBB
    photo_path: str | None = None
    data_label: str | None = None  # 예: "재산"
    data_value: str | None = None  # 예: "127억"

    def validate(self) -> None:
        if not 1 <= len(self.name) <= 20:
            raise ValueError(f"name length must be 1~20 (got {len(self.name)})")
        if not (self.party_color.startswith("#") and len(self.party_color) == 7):
            raise ValueError(f"party_color must be #RRGGBB (got {self.party_color})")
        if (self.data_label is None) != (self.data_value is None):
            raise ValueError(
                "data_label and data_value must be set together (or both None)"
            )

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "name": self.name,
            "party": self.party,
            "party_color": self.party_color,
        }
        if self.photo_path is not None:
            d["photo_path"] = self.photo_path
        if self.data_label is not None:
            d["data_label"] = self.data_label
        if self.data_value is not None:
            d["data_value"] = self.data_value
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PoliticianCard":
        return cls(
            name=str(data["name"]),
            party=str(data["party"]),
            party_color=str(data.get("party_color") or data.get("partyColor")),
            photo_path=data.get("photo_path") or data.get("photoPath"),
            data_label=data.get("data_label") or data.get("dataLabel"),
            data_value=data.get("data_value") or data.get("dataValue"),
        )
