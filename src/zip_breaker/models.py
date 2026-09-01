from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CrackStatus(str, Enum):
    FOUND = "found"
    NOT_FOUND = "not_found"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class ProgressUpdate:
    """Estado periódico consumível tanto pelo terminal quanto por uma GUI."""

    attempts: int
    total: int | None
    elapsed_seconds: float

    @property
    def attempts_per_second(self) -> float:
        if self.elapsed_seconds <= 0:
            return 0.0
        return self.attempts / self.elapsed_seconds

    @property
    def percentage(self) -> float | None:
        if not self.total:
            return None
        return min(100.0, self.attempts * 100 / self.total)


@dataclass(frozen=True, slots=True)
class CrackResult:
    status: CrackStatus
    attempts: int
    elapsed_seconds: float
    password: str | None = None

    @property
    def found(self) -> bool:
        return self.status is CrackStatus.FOUND

