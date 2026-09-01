from __future__ import annotations

from collections.abc import Callable, Iterable
from time import monotonic
from typing import Protocol

from .archive import ArchivePasswordTester
from .control import CrackControl
from .models import CrackResult, CrackStatus, ProgressUpdate

ProgressCallback = Callable[[ProgressUpdate], None]


class PasswordTester(Protocol):
    def test(self, password: str) -> bool: ...


class ZipPasswordCracker:
    """Serviço sem dependência de interface, apropriado para CLI e GUI."""

    def __init__(
        self,
        archive_path: str,
        *,
        progress_interval: int = 100,
        tester: PasswordTester | None = None,
    ) -> None:
        if progress_interval < 1:
            raise ValueError("progress_interval deve ser maior que zero")
        self._tester = tester or ArchivePasswordTester(archive_path)
        self.progress_interval = progress_interval

    def crack(
        self,
        passwords: Iterable[str],
        *,
        total: int | None = None,
        on_progress: ProgressCallback | None = None,
        control: CrackControl | None = None,
    ) -> CrackResult:
        control = control or CrackControl()
        started_at = monotonic()
        attempts = 0

        for candidate in passwords:
            if not control.wait_until_runnable():
                return CrackResult(
                    CrackStatus.CANCELLED, attempts, monotonic() - started_at
                )

            attempts += 1
            if self._tester.test(candidate):
                elapsed = monotonic() - started_at
                self._notify(on_progress, attempts, total, elapsed)
                return CrackResult(
                    CrackStatus.FOUND,
                    attempts,
                    elapsed,
                    password=candidate,
                )

            if attempts % self.progress_interval == 0:
                self._notify(
                    on_progress, attempts, total, monotonic() - started_at
                )

        elapsed = monotonic() - started_at
        self._notify(on_progress, attempts, total, elapsed)
        return CrackResult(CrackStatus.NOT_FOUND, attempts, elapsed)

    @staticmethod
    def _notify(
        callback: ProgressCallback | None,
        attempts: int,
        total: int | None,
        elapsed: float,
    ) -> None:
        if callback is not None:
            callback(ProgressUpdate(attempts, total, elapsed))
