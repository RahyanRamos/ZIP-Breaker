from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from .exceptions import EmptyWordlistError, InputFileError, WordlistEncodingError


@dataclass(frozen=True, slots=True)
class Wordlist:
    """Wordlist reiniciável e processada linha a linha para limitar o uso de RAM."""

    path: Path
    encoding: str = "utf-8-sig"

    def __init__(self, path: str | Path, encoding: str = "utf-8-sig") -> None:
        object.__setattr__(self, "path", Path(path).expanduser())
        object.__setattr__(self, "encoding", encoding)
        self._validate_path()

    def _validate_path(self) -> None:
        if not self.path.exists():
            raise InputFileError(f"Wordlist não encontrada: {self.path}")
        if not self.path.is_file():
            raise InputFileError(f"A wordlist não é um arquivo: {self.path}")
        try:
            "".encode(self.encoding)
        except LookupError as exc:
            raise WordlistEncodingError(
                f"Codificação de wordlist desconhecida: {self.encoding}"
            ) from exc

    def __iter__(self) -> Iterator[str]:
        try:
            with self.path.open("r", encoding=self.encoding, errors="strict", newline="") as stream:
                for line in stream:
                    candidate = line.rstrip("\r\n")
                    if candidate:
                        yield candidate
        except UnicodeError as exc:
            raise WordlistEncodingError(
                f"Não foi possível ler {self.path} como {self.encoding}. "
                "Informe a codificação correta com --encoding."
            ) from exc
        except OSError as exc:
            raise InputFileError(f"Não foi possível ler a wordlist: {exc}") from exc

    def count(self) -> int:
        total = sum(1 for _ in self)
        if total == 0:
            raise EmptyWordlistError("A wordlist não contém senhas não vazias.")
        return total

