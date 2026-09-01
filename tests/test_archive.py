from __future__ import annotations

import shutil
import struct
import unittest
import zipfile
import zlib
from pathlib import Path
from uuid import uuid4

from zip_breaker.archive import (
    ArchivePasswordTester,
    _validate_extraction_members,
    validate_archive_path,
)
from zip_breaker.exceptions import (
    ArchiveNotEncryptedError,
    InputFileError,
    InvalidArchiveError,
    UnsafeArchiveError,
)

try:
    import pyzipper
except ImportError:  # pragma: no cover
    pyzipper = None


def _zipcrypto_encrypt(data: bytes, password: bytes) -> bytes:
    """Implementação mínima de escrita usada somente para criar a fixture."""
    table = []
    for value in range(256):
        crc = value
        for _ in range(8):
            crc = (crc >> 1) ^ (0xEDB88320 if crc & 1 else 0)
        table.append(crc)

    keys = [0x12345678, 0x23456789, 0x34567890]

    def update(value: int) -> None:
        keys[0] = (keys[0] >> 8) ^ table[(keys[0] ^ value) & 0xFF]
        keys[1] = (keys[1] + (keys[0] & 0xFF)) & 0xFFFFFFFF
        keys[1] = (keys[1] * 134775813 + 1) & 0xFFFFFFFF
        keys[2] = (keys[2] >> 8) ^ table[(keys[2] ^ (keys[1] >> 24)) & 0xFF]

    for value in password:
        update(value)

    encrypted = bytearray()
    for value in data:
        temporary = keys[2] | 2
        encrypted.append(value ^ ((temporary * (temporary ^ 1)) >> 8) & 0xFF)
        update(value)
    return bytes(encrypted)


def _write_zipcrypto_fixture(path: Path, password: bytes) -> None:
    """Gera um ZIP Store/ZipCrypto válido sem depender de executável externo."""
    filename = b"dados.txt"
    content = b"conteudo tradicional protegido"
    crc = zlib.crc32(content) & 0xFFFFFFFF
    header_plaintext = bytes(range(11)) + bytes([crc >> 24])
    encrypted = _zipcrypto_encrypt(header_plaintext + content, password)
    compressed_size = len(encrypted)

    local = struct.pack(
        "<IHHHHHIIIHH",
        0x04034B50,
        20,
        1,
        0,
        0,
        0,
        crc,
        compressed_size,
        len(content),
        len(filename),
        0,
    ) + filename + encrypted
    central = struct.pack(
        "<IHHHHHHIIIHHHHHII",
        0x02014B50,
        20,
        20,
        1,
        0,
        0,
        0,
        crc,
        compressed_size,
        len(content),
        len(filename),
        0,
        0,
        0,
        0,
        0,
        0,
    ) + filename
    end = struct.pack(
        "<IHHHHIIH",
        0x06054B50,
        0,
        0,
        1,
        1,
        len(central),
        len(local),
        0,
    )
    path.write_bytes(local + central + end)


class ArchiveTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path.cwd() / ".test-runtime" / uuid4().hex
        self.root.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, self.root, True)

    def test_missing_archive_is_rejected(self) -> None:
        with self.assertRaises(InputFileError):
            validate_archive_path(self.root / "missing.zip")

    def test_non_zip_is_rejected(self) -> None:
        path = self.root / "fake.zip"
        path.write_text("isto não é um zip", encoding="utf-8")
        with self.assertRaises(InvalidArchiveError):
            validate_archive_path(path)

    def test_unencrypted_archive_is_rejected(self) -> None:
        path = self.root / "plain.zip"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("arquivo.txt", "conteúdo")
        with self.assertRaises(ArchiveNotEncryptedError):
            ArchivePasswordTester(path)

    def test_zip_slip_path_is_rejected(self) -> None:
        malicious = zipfile.ZipInfo("../fora.txt")
        with self.assertRaises(UnsafeArchiveError):
            _validate_extraction_members([malicious], self.root / "destino")

    def test_zipcrypto_password_is_really_validated(self) -> None:
        path = self.root / "tradicional.zip"
        _write_zipcrypto_fixture(path, b"senha123")

        tester = ArchivePasswordTester(path)

        self.assertFalse(tester.uses_aes)
        self.assertFalse(tester.test("incorreta"))
        self.assertTrue(tester.test("senha123"))

    @unittest.skipIf(pyzipper is None, "pyzipper não instalado")
    def test_aes_password_is_really_validated(self) -> None:
        path = self.root / "aes.zip"
        assert pyzipper is not None
        with pyzipper.AESZipFile(
            path,
            "w",
            compression=pyzipper.ZIP_DEFLATED,
            encryption=pyzipper.WZ_AES,
        ) as archive:
            archive.setpassword("segredo-á".encode("utf-8"))
            archive.setencryption(pyzipper.WZ_AES, nbits=256)
            archive.writestr("dados.txt", "conteúdo protegido")

        tester = ArchivePasswordTester(path)

        self.assertTrue(tester.uses_aes)
        self.assertFalse(tester.test("incorreta"))
        self.assertTrue(tester.test("segredo-á"))


if __name__ == "__main__":
    unittest.main()
