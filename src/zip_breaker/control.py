from __future__ import annotations

from threading import Event


class CrackControl:
    """Controle cooperativo de pausa/cancelamento, pronto para uso por uma GUI."""

    def __init__(self) -> None:
        self._cancelled = Event()
        self._running = Event()
        self._running.set()

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled.is_set()

    def cancel(self) -> None:
        self._cancelled.set()
        self._running.set()

    def pause(self) -> None:
        self._running.clear()

    def resume(self) -> None:
        self._running.set()

    def wait_until_runnable(self) -> bool:
        """Espera enquanto pausado e retorna False quando houver cancelamento."""
        while not self._cancelled.is_set():
            if self._running.wait(timeout=0.1):
                return not self._cancelled.is_set()
        return False

