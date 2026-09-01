from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence, TextIO

from . import __version__
from .archive import extract_archive
from .cracker import ZipPasswordCracker
from .exceptions import ZipBreakerError
from .models import CrackStatus, ProgressUpdate
from .wordlist import Wordlist


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="zip-breaker",
        description=(
            "Recupera, por wordlist, a senha de um arquivo ZIP que você possui "
            "ou tem autorização explícita para testar."
        ),
    )
    parser.add_argument("arquivo_zip", type=Path, help="arquivo ZIP protegido")
    parser.add_argument("wordlist", type=Path, help="arquivo com uma senha por linha")
    parser.add_argument(
        "--encoding",
        default="utf-8-sig",
        help="codificação da wordlist (padrão: utf-8-sig)",
    )
    parser.add_argument(
        "--extrair-para",
        type=Path,
        metavar="DIRETORIO",
        help="extrai o ZIP neste diretório quando a senha for encontrada",
    )
    parser.add_argument(
        "--progresso-a-cada",
        type=int,
        default=100,
        metavar="N",
        help="atualiza o progresso a cada N tentativas (padrão: 100)",
    )
    parser.add_argument("--sem-progresso", action="store_true")
    parser.add_argument("--version", action="version", version=__version__)
    return parser


class ConsoleProgress:
    def __init__(self, stream: TextIO) -> None:
        self.stream = stream

    def __call__(self, update: ProgressUpdate) -> None:
        if update.percentage is None:
            amount = f"{update.attempts} tentativas"
        else:
            amount = f"{update.attempts}/{update.total} ({update.percentage:.1f}%)"
        print(
            f"\rProgresso: {amount} | {update.attempts_per_second:.0f} senhas/s",
            end="",
            file=self.stream,
            flush=True,
        )

    def finish_line(self) -> None:
        print(file=self.stream)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.progresso_a_cada < 1:
        parser.error("--progresso-a-cada deve ser maior que zero")

    progress = None if args.sem_progresso else ConsoleProgress(sys.stderr)
    try:
        wordlist = Wordlist(args.wordlist, encoding=args.encoding)
        total = wordlist.count()
        cracker = ZipPasswordCracker(
            str(args.arquivo_zip), progress_interval=args.progresso_a_cada
        )
        result = cracker.crack(wordlist, total=total, on_progress=progress)
    except KeyboardInterrupt:
        if progress:
            progress.finish_line()
        print("Operação cancelada pelo usuário.", file=sys.stderr)
        return 130
    except ZipBreakerError as exc:
        if progress:
            progress.finish_line()
        print(f"Erro: {exc}", file=sys.stderr)
        return 2

    if progress:
        progress.finish_line()

    if result.status is CrackStatus.FOUND:
        print(f"Senha encontrada: {result.password}")
        print(
            f"Tentativas: {result.attempts} | Tempo: {result.elapsed_seconds:.2f}s"
        )
        if args.extrair_para:
            try:
                destination = extract_archive(
                    args.arquivo_zip, args.extrair_para, result.password or ""
                )
            except ZipBreakerError as exc:
                print(f"Senha encontrada, mas a extração falhou: {exc}", file=sys.stderr)
                return 2
            print(f"Arquivos extraídos em: {destination}")
        return 0

    print(
        f"Senha não encontrada após {result.attempts} tentativas "
        f"({result.elapsed_seconds:.2f}s)."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

