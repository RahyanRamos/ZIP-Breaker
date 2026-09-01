from __future__ import annotations

import io
import shutil
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from uuid import uuid4

from zip_breaker.cli import main

try:
    import pyzipper
except ImportError:  # pragma: no cover
    pyzipper = None


class CliTests(unittest.TestCase):
    def test_missing_inputs_return_controlled_error(self) -> None:
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            exit_code = main(["inexistente.zip", "inexistente.txt", "--sem-progresso"])
        self.assertEqual(exit_code, 2)
        self.assertIn("Erro:", stderr.getvalue())

    @unittest.skipIf(pyzipper is None, "pyzipper não instalado")
    def test_full_aes_cli_flow_finds_password_and_extracts(self) -> None:
        root = Path.cwd() / ".test-runtime" / uuid4().hex
        root.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, root, True)
        archive_path = root / "protegido.zip"
        wordlist_path = root / "wordlist.txt"
        destination = root / "extraido"
        wordlist_path.write_text("errada\nminha-senha\noutra\n", encoding="utf-8")

        assert pyzipper is not None
        with pyzipper.AESZipFile(
            archive_path,
            "w",
            compression=pyzipper.ZIP_DEFLATED,
            encryption=pyzipper.WZ_AES,
        ) as archive:
            archive.setpassword(b"minha-senha")
            archive.setencryption(pyzipper.WZ_AES, nbits=256)
            archive.writestr("documento.txt", "arquivo recuperado")

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main(
                [
                    str(archive_path),
                    str(wordlist_path),
                    "--extrair-para",
                    str(destination),
                    "--sem-progresso",
                ]
            )

        self.assertEqual(exit_code, 0)
        self.assertIn("Senha encontrada: minha-senha", stdout.getvalue())
        self.assertEqual(
            (destination / "documento.txt").read_text(encoding="utf-8"),
            "arquivo recuperado",
        )


if __name__ == "__main__":
    unittest.main()
