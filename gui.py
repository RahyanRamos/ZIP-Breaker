"""Interface gráfica (Tkinter) para o ZIP Breaker.

Executa o núcleo `ZipPasswordCracker` do backend em uma thread de trabalho e
recebe os eventos de progresso na thread principal por meio de uma fila, como
recomendado no README do projeto.
"""

from __future__ import annotations

import queue
import sys
import threading
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# Permite rodar "python gui.py" mesmo sem ter feito "pip install -e ."
_SRC = Path(__file__).resolve().parent / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from zip_breaker import CrackControl, Wordlist, ZipPasswordCracker
from zip_breaker.archive import extract_archive
from zip_breaker.exceptions import ZipBreakerError
from zip_breaker.models import CrackStatus, ProgressUpdate


class ZipBreakerGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("ZIP Breaker — Recuperação de senha por wordlist")
        self.root.geometry("640x560")
        self.root.minsize(560, 520)

        # Estado de execução
        self.control: CrackControl | None = None
        self.worker: threading.Thread | None = None
        self.events: queue.Queue = queue.Queue()
        self.paused = False

        self._build_widgets()

    # ------------------------------------------------------------------ UI
    def _build_widgets(self) -> None:
        pad = {"padx": 10, "pady": 6}

        titulo = ttk.Label(
            self.root,
            text="ZIP Breaker",
            font=("Segoe UI", 18, "bold"),
        )
        titulo.pack(pady=(14, 0))
        ttk.Label(
            self.root,
            text="Ataque de dicionário em ZIP próprio ou autorizado",
        ).pack(pady=(0, 8))

        # ---- Seleção de arquivos
        frm = ttk.LabelFrame(self.root, text="Entradas")
        frm.pack(fill="x", **pad)

        self.zip_var = tk.StringVar()
        self.wl_var = tk.StringVar()
        self.enc_var = tk.StringVar(value="utf-8-sig")

        self._file_row(frm, "Arquivo ZIP:", self.zip_var, self._pick_zip, 0)
        self._file_row(frm, "Wordlist:", self.wl_var, self._pick_wordlist, 1)

        ttk.Label(frm, text="Codificação:").grid(row=2, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(frm, textvariable=self.enc_var, width=18).grid(
            row=2, column=1, sticky="w", padx=8, pady=6
        )
        frm.columnconfigure(1, weight=1)

        # ---- Extração opcional
        self.extrair_var = tk.BooleanVar(value=False)
        self.dest_var = tk.StringVar()
        frm_ext = ttk.LabelFrame(self.root, text="Extração (opcional)")
        frm_ext.pack(fill="x", **pad)
        ttk.Checkbutton(
            frm_ext,
            text="Extrair o conteúdo quando a senha for encontrada",
            variable=self.extrair_var,
            command=self._toggle_extract,
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=8, pady=(6, 2))
        ttk.Label(frm_ext, text="Pasta destino:").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        self.dest_entry = ttk.Entry(frm_ext, textvariable=self.dest_var, state="disabled")
        self.dest_entry.grid(row=1, column=1, sticky="ew", padx=8, pady=6)
        self.dest_btn = ttk.Button(
            frm_ext, text="Procurar…", command=self._pick_dest, state="disabled"
        )
        self.dest_btn.grid(row=1, column=2, padx=8, pady=6)
        frm_ext.columnconfigure(1, weight=1)

        # ---- Botões de ação
        frm_btn = ttk.Frame(self.root)
        frm_btn.pack(fill="x", **pad)
        self.start_btn = ttk.Button(frm_btn, text="▶ Quebrar senha", command=self._start)
        self.start_btn.pack(side="left", padx=4)
        self.pause_btn = ttk.Button(
            frm_btn, text="⏸ Pausar", command=self._toggle_pause, state="disabled"
        )
        self.pause_btn.pack(side="left", padx=4)
        self.cancel_btn = ttk.Button(
            frm_btn, text="⏹ Cancelar", command=self._cancel, state="disabled"
        )
        self.cancel_btn.pack(side="left", padx=4)

        # ---- Progresso
        frm_prog = ttk.LabelFrame(self.root, text="Progresso")
        frm_prog.pack(fill="x", **pad)
        self.progress = ttk.Progressbar(frm_prog, maximum=100, value=0)
        self.progress.pack(fill="x", padx=8, pady=(8, 4))
        self.stats_var = tk.StringVar(value="Aguardando…")
        ttk.Label(frm_prog, textvariable=self.stats_var).pack(anchor="w", padx=8, pady=(0, 8))

        # ---- Resultado
        self.result_var = tk.StringVar(value="")
        self.result_lbl = ttk.Label(
            self.root, textvariable=self.result_var, font=("Segoe UI", 12, "bold")
        )
        self.result_lbl.pack(fill="x", padx=12, pady=8)

    def _file_row(self, parent, label, var, cmd, row) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(parent, textvariable=var).grid(row=row, column=1, sticky="ew", padx=8, pady=6)
        ttk.Button(parent, text="Procurar…", command=cmd).grid(row=row, column=2, padx=8, pady=6)

    # ------------------------------------------------------------- Ações UI
    def _pick_zip(self) -> None:
        caminho = filedialog.askopenfilename(
            title="Selecione o arquivo ZIP",
            filetypes=[("Arquivos ZIP", "*.zip"), ("Todos os arquivos", "*.*")],
        )
        if caminho:
            self.zip_var.set(caminho)

    def _pick_wordlist(self) -> None:
        caminho = filedialog.askopenfilename(
            title="Selecione a wordlist",
            filetypes=[("Arquivos de texto", "*.txt"), ("Todos os arquivos", "*.*")],
        )
        if caminho:
            self.wl_var.set(caminho)

    def _pick_dest(self) -> None:
        pasta = filedialog.askdirectory(title="Selecione a pasta de destino")
        if pasta:
            self.dest_var.set(pasta)

    def _toggle_extract(self) -> None:
        estado = "normal" if self.extrair_var.get() else "disabled"
        self.dest_entry.configure(state=estado)
        self.dest_btn.configure(state=estado)

    # ----------------------------------------------------------- Execução
    def _start(self) -> None:
        zip_path = self.zip_var.get().strip()
        wl_path = self.wl_var.get().strip()
        encoding = self.enc_var.get().strip() or "utf-8-sig"

        if not zip_path or not wl_path:
            messagebox.showwarning("Campos obrigatórios", "Selecione o ZIP e a wordlist.")
            return
        if self.extrair_var.get() and not self.dest_var.get().strip():
            messagebox.showwarning("Extração", "Informe a pasta de destino da extração.")
            return

        # Reset da interface
        self.progress.configure(value=0)
        self.result_var.set("")
        self.result_lbl.configure(foreground="black")
        self.stats_var.set("Preparando…")
        self.paused = False
        self.pause_btn.configure(text="⏸ Pausar")

        self.control = CrackControl()
        self._set_running(True)

        self.worker = threading.Thread(
            target=self._run_crack,
            args=(zip_path, wl_path, encoding),
            daemon=True,
        )
        self.worker.start()
        self.root.after(100, self._poll_events)

    def _run_crack(self, zip_path: str, wl_path: str, encoding: str) -> None:
        """Roda na thread de trabalho. Comunica-se pela fila self.events."""
        try:
            wordlist = Wordlist(wl_path, encoding=encoding)
            total = wordlist.count()
            cracker = ZipPasswordCracker(zip_path, progress_interval=25)
            resultado = cracker.crack(
                wordlist,
                total=total,
                on_progress=lambda ev: self.events.put(("progress", ev)),
                control=self.control,
            )
            self.events.put(("done", resultado))
        except ZipBreakerError as exc:
            self.events.put(("error", str(exc)))
        except Exception as exc:  # rede de segurança para a demonstração
            self.events.put(("error", f"Erro inesperado: {exc}"))

    def _poll_events(self) -> None:
        try:
            while True:
                tipo, dado = self.events.get_nowait()
                if tipo == "progress":
                    self._on_progress(dado)
                elif tipo == "done":
                    self._on_done(dado)
                    return
                elif tipo == "error":
                    self._on_error(dado)
                    return
        except queue.Empty:
            pass
        # Continua consultando enquanto o worker estiver vivo
        if self.worker and self.worker.is_alive():
            self.root.after(100, self._poll_events)

    # --------------------------------------------------------- Callbacks
    def _on_progress(self, ev: ProgressUpdate) -> None:
        if ev.percentage is not None:
            self.progress.configure(value=ev.percentage)
            alvo = f"{ev.attempts}/{ev.total} ({ev.percentage:.1f}%)"
        else:
            alvo = f"{ev.attempts} tentativas"
        self.stats_var.set(
            f"{alvo}  |  {ev.attempts_per_second:.0f} senhas/s  |  {ev.elapsed_seconds:.1f}s"
        )

    def _on_done(self, resultado) -> None:
        self._set_running(False)
        if resultado.status is CrackStatus.FOUND:
            self.progress.configure(value=100)
            self.result_var.set(f"✅ Senha encontrada: {resultado.password}")
            self.result_lbl.configure(foreground="#1a7f37")
            self.stats_var.set(
                f"{resultado.attempts} tentativas  |  {resultado.elapsed_seconds:.2f}s"
            )
            if self.extrair_var.get():
                self._extrair(resultado.password)
        elif resultado.status is CrackStatus.CANCELLED:
            self.result_var.set("⏹ Operação cancelada.")
            self.result_lbl.configure(foreground="#9a6700")
        else:
            self.result_var.set(
                f"❌ Senha não encontrada após {resultado.attempts} tentativas."
            )
            self.result_lbl.configure(foreground="#cf222e")

    def _extrair(self, senha: str) -> None:
        try:
            destino = extract_archive(self.zip_var.get(), self.dest_var.get(), senha or "")
            messagebox.showinfo("Extração concluída", f"Arquivos extraídos em:\n{destino}")
        except ZipBreakerError as exc:
            messagebox.showerror("Falha na extração", str(exc))

    def _on_error(self, mensagem: str) -> None:
        self._set_running(False)
        self.stats_var.set("Erro.")
        self.result_var.set(f"❌ {mensagem}")
        self.result_lbl.configure(foreground="#cf222e")
        messagebox.showerror("Erro", mensagem)

    # ---------------------------------------------------- Pausar/Cancelar
    def _toggle_pause(self) -> None:
        if not self.control:
            return
        if self.paused:
            self.control.resume()
            self.paused = False
            self.pause_btn.configure(text="⏸ Pausar")
            self.stats_var.set("Retomado…")
        else:
            self.control.pause()
            self.paused = True
            self.pause_btn.configure(text="▶ Retomar")
            self.stats_var.set("Pausado.")

    def _cancel(self) -> None:
        if self.control:
            self.control.cancel()
            self.stats_var.set("Cancelando…")

    def _set_running(self, rodando: bool) -> None:
        self.start_btn.configure(state="disabled" if rodando else "normal")
        self.pause_btn.configure(state="normal" if rodando else "disabled")
        self.cancel_btn.configure(state="normal" if rodando else "disabled")


def main() -> None:
    root = tk.Tk()
    try:
        ttk.Style().theme_use("clam")
    except tk.TclError:
        pass
    ZipBreakerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()