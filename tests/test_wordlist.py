from __future__ import annotations

import shutil
import unittest
from pathlib import Path
from uuid import uuid4

from zip_breaker.exceptions import EmptyWordlistError, InputFileError, WordlistEncodingError
from zip_breaker.wordlist import Wordlist


class WordlistTests(unittest.TestCase):
    def setUp(self) -> None:
        # tempfile aplica ACLs incompatíveis com alguns sandboxes no Windows.
        self.root = Path.cwd() / ".test-runtime" / uuid4().hex
        self.root.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, self.root, True)

    def test_reads_lazily_ignores_empty_lines_and_preserves_spaces(self) -> None:
        path = self.root / "senhas.txt"
        path.write_text("primeira\n\n senha com espaços \r\nterceira", encoding="utf-8")
        wordlist = Wordlist(path)

        self.assertEqual(
            list(wordlist), ["primeira", " senha com espaços ", "terceira"]
        )
        self.assertEqual(wordlist.count(), 3)

    def test_missing_file_is_rejected(self) -> None:
        with self.assertRaises(InputFileError):
            Wordlist(self.root / "inexistente.txt")

    def test_empty_wordlist_is_rejected(self) -> None:
        path = self.root / "vazia.txt"
        path.write_text("\n\r\n", encoding="utf-8")
        with self.assertRaises(EmptyWordlistError):
            Wordlist(path).count()

    def test_wrong_encoding_has_domain_error(self) -> None:
        path = self.root / "latin1.txt"
        path.write_bytes("ação".encode("latin-1"))
        with self.assertRaises(WordlistEncodingError):
            list(Wordlist(path, encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
