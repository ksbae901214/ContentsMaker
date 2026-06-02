"""BlindPost JSON schema validation.

Validates input data against BlindPost schema before saving.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from src.config.settings import MIN_BODY_LENGTH


@dataclass(frozen=True)
class ValidationError:
    """A single validation error."""
    field: str
    message: str


@dataclass(frozen=True)
class ValidationResult:
    """Result of validating a BlindPost dict."""
    errors: tuple[ValidationError, ...] = field(default_factory=tuple)
    warnings: tuple[ValidationError, ...] = field(default_factory=tuple)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def error_messages(self) -> list[str]:
        return [f"[{e.field}] {e.message}" for e in self.errors]

    def warning_messages(self) -> list[str]:
        return [f"[{w.field}] {w.message}" for w in self.warnings]


def validate_blind_post(data: dict) -> ValidationResult:
    """Validate a dict against BlindPost schema.

    Returns ValidationResult with errors (blocking) and warnings (non-blocking).
    """
    errors: list[ValidationError] = []
    warnings: list[ValidationError] = []

    # Required fields
    if "title" not in data:
        errors.append(ValidationError("title", "필수 필드가 누락되었습니다"))
    elif not isinstance(data["title"], str):
        errors.append(ValidationError("title", "문자열이어야 합니다"))
    elif not data["title"].strip():
        errors.append(ValidationError("title", "비어있을 수 없습니다"))

    if "body" not in data:
        errors.append(ValidationError("body", "필수 필드가 누락되었습니다"))
    elif not isinstance(data["body"], str):
        errors.append(ValidationError("body", "문자열이어야 합니다"))
    elif not data["body"].strip():
        errors.append(ValidationError("body", "비어있을 수 없습니다"))
    elif len(data["body"].strip()) < MIN_BODY_LENGTH:
        warnings.append(
            ValidationError(
                "body",
                f"본문이 너무 짧습니다 (최소 {MIN_BODY_LENGTH}자, 현재 {len(data['body'].strip())}자)",
            )
        )

    # Optional fields with type checks
    if "author" in data and not isinstance(data["author"], str):
        errors.append(ValidationError("author", "문자열이어야 합니다"))

    if "url" in data and not isinstance(data["url"], str):
        errors.append(ValidationError("url", "문자열이어야 합니다"))

    # Comments validation
    if "comments" in data:
        if not isinstance(data["comments"], list):
            errors.append(ValidationError("comments", "배열이어야 합니다"))
        else:
            for i, comment in enumerate(data["comments"]):
                if not isinstance(comment, dict):
                    errors.append(
                        ValidationError(f"comments[{i}]", "객체여야 합니다")
                    )
                    continue
                if "text" not in comment:
                    errors.append(
                        ValidationError(
                            f"comments[{i}].text", "필수 필드가 누락되었습니다"
                        )
                    )
                elif not isinstance(comment["text"], str):
                    errors.append(
                        ValidationError(
                            f"comments[{i}].text", "문자열이어야 합니다"
                        )
                    )
                if "likes" in comment and not isinstance(comment["likes"], int):
                    errors.append(
                        ValidationError(
                            f"comments[{i}].likes", "정수여야 합니다"
                        )
                    )

    return ValidationResult(
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
