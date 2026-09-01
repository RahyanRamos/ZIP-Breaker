from __future__ import annotations

import os
import stat
import zipfile
import zlib
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any

from .exceptions import (
    ArchiveNotEncryptedError,
    ArchiveReadError,
    InputFileError,
    InvalidArchiveError,
    UnsafeArchiveError,
    UnsupportedEncryptionError,
)

try:
    import pyzipper
except ImportError:  # pragma: no cover - exercitado apenas em instalação incompleta
    pyzipper = None  # type: ignore[assignment]

AES_EXTRA_FIELD_ID = 0x9901


def validate_archive_path(path: str | Path) -> Path:
    archive = Path(path).expanduser()
    if not archive.exists():
        raise InputFileError(f"Arquivo ZIP não encontrado: {archive}")
    if not archive.is_file():
        raise InputFileError(f"O caminho informado não é um arquivo: {archive}")
    try:
        is_zip = zipfile.is_zipfile(archive)
    except OSError as exc:
        raise InputFileError(f"Não foi possível ler o arquivo ZIP: {exc}") from exc
    if not is_zip:
        raise InvalidArchiveError(f"O arquivo não é um ZIP válido: {archive}")
    return archive


def _extra_field_ids(extra: bytes) -> set[int]:
    identifiers: set[int] = set()
    cursor = 0
    while cursor + 4 <= len(extra):
        identifier = int.from_bytes(extra[cursor : cursor + 2], "little")
        size = int.from_bytes(extra[cursor + 2 : cursor + 4], "little")
        identifiers.add(identifier)
        cursor += 4 + size
    return identifiers


def is_aes_member(info: zipfile.ZipInfo) -> bool:
    return info.compress_type == 99 or AES_EXTRA_FIELD_ID in _extra_field_ids(info.extra)


class ArchivePasswordTester:
    """Abre um membro pequeno do ZIP até o fim, incluindo validação CRC/HMAC."""

    def __init__(self, archive_path: str | Path) -> None:
        self.archive_path = validate_archive_path(archive_path)
        try:
            with zipfile.ZipFile(self.archive_path) as archive:
                encrypted = [
                    info
                    for info in archive.infolist()
                    if info.flag_bits & 0x1 and not info.is_dir()
                ]
        except (zipfile.BadZipFile, OSError) as exc:
            raise InvalidArchiveError(f"Não foi possível analisar o ZIP: {exc}") from exc

        if not encrypted:
            raise ArchiveNotEncryptedError(
                "O ZIP não contém arquivos protegidos por senha; não há o que recuperar."
            )

        self.member = min(encrypted, key=lambda info: info.file_size)
        self.uses_aes = is_aes_member(self.member)
        if self.uses_aes and pyzipper is None:
            raise UnsupportedEncryptionError(
                "Este ZIP usa AES. Instale a dependência com: pip install pyzipper"
            )

    def _open_archive(self) -> AbstractContextManager[Any]:
        if self.uses_aes:
            assert pyzipper is not None
            return pyzipper.AESZipFile(self.archive_path, "r")
        return zipfile.ZipFile(self.archive_path, "r")

    def test(self, password: str) -> bool:
        encoded = password.encode("utf-8")
        try:
            with self._open_archive() as archive:
                with archive.open(self.member.filename, "r", pwd=encoded) as member:
                    while member.read(64 * 1024):
                        pass
            return True
        except RuntimeError as exc:
            message = str(exc).lower()
            if any(marker in message for marker in ("password", "hmac", "decrypt")):
                return False
            raise ArchiveReadError(f"Falha inesperada ao ler o ZIP: {exc}") from exc
        except NotImplementedError as exc:
            raise UnsupportedEncryptionError(
                f"Método de compactação/criptografia não suportado: {exc}"
            ) from exc
        except (zipfile.BadZipFile, zlib.error):
            # Uma senha incorreta pode, por coincidência, passar pelo byte de
            # verificação do ZipCrypto e falhar somente no DEFLATE/CRC.
            return False
        except OSError as exc:
            raise ArchiveReadError(f"O ZIP parece estar corrompido ou ilegível: {exc}") from exc


def _validate_extraction_members(infos: list[zipfile.ZipInfo], destination: Path) -> None:
    destination_resolved = destination.resolve()
    for info in infos:
        unix_mode = info.external_attr >> 16
        if stat.S_ISLNK(unix_mode):
            raise UnsafeArchiveError(
                f"Extração recusada: o ZIP contém link simbólico ({info.filename})."
            )
        target = (destination / info.filename).resolve()
        try:
            inside_destination = os.path.commonpath(
                (str(destination_resolved), str(target))
            ) == str(destination_resolved)
        except ValueError:
            inside_destination = False
        if not inside_destination:
            raise UnsafeArchiveError(
                f"Extração recusada: caminho inseguro no ZIP ({info.filename})."
            )


def extract_archive(
    archive_path: str | Path, destination: str | Path, password: str
) -> Path:
    """Extrai somente após validar todos os caminhos contra Zip Slip e symlinks."""
    archive_path = validate_archive_path(archive_path)
    destination_path = Path(destination).expanduser()
    destination_path.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(archive_path) as inspector:
        infos = inspector.infolist()
        uses_aes = any(is_aes_member(info) for info in infos)
    _validate_extraction_members(infos, destination_path)

    try:
        if uses_aes:
            if pyzipper is None:
                raise UnsupportedEncryptionError(
                    "Este ZIP usa AES. Instale a dependência pyzipper."
                )
            opener: Any = pyzipper.AESZipFile
        else:
            opener = zipfile.ZipFile
        with opener(archive_path, "r") as archive:
            archive.extractall(destination_path, pwd=password.encode("utf-8"))
    except (zipfile.BadZipFile, RuntimeError, OSError) as exc:
        raise ArchiveReadError(f"Falha ao extrair o ZIP: {exc}") from exc
    return destination_path.resolve()
