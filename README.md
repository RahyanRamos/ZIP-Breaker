# ZIP Breaker

Aplicação Python para recuperar a senha de **seus próprios arquivos ZIP** por
ataque de dicionário (wordlist). O projeto foi organizado para uma atividade de
cybersegurança e não deve ser usado em arquivos sem autorização do proprietário.

O núcleo não depende da interface de terminal. Assim, uma interface gráfica pode
importar `ZipPasswordCracker`, receber atualizações de progresso e controlar
pausa/cancelamento sem duplicar a lógica.

## Recursos

- ZIP tradicional (ZipCrypto) por meio da biblioteca padrão `zipfile`;
- ZIP com AES-128/192/256 por meio de `pyzipper`;
- wordlists lidas linha a linha, sem carregá-las inteiras na memória;
- progresso, pausa e cancelamento cooperativos para integração futura com GUI;
- extração opcional após encontrar a senha;
- bloqueio de caminhos `../`, caminhos absolutos e links simbólicos na extração;
- mensagens amigáveis para arquivos inexistentes, ZIP inválido, ZIP sem senha,
  wordlist vazia/codificação incorreta e criptografia não suportada;
- testes unitários e teste real com ZIP AES criado durante a suíte.

## Requisitos e instalação

- Python 3.10 ou superior.

No PowerShell, dentro da pasta do projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

## Uso pelo terminal

Crie uma wordlist de texto com uma senha por linha e execute:

```powershell
zip-breaker "meu-arquivo.zip" "minhas-senhas.txt"
```

Também funciona sem instalar o comando, desde que o pacote esteja instalado:

```powershell
python -m zip_breaker "meu-arquivo.zip" "minhas-senhas.txt"
```

Para extrair automaticamente depois de encontrar a senha:

```powershell
zip-breaker "meu-arquivo.zip" "minhas-senhas.txt" --extrair-para recuperado
```

Wordlist em outra codificação:

```powershell
zip-breaker arquivo.zip wordlist.txt --encoding latin-1
```

Consulte todas as opções com `zip-breaker --help`. Os códigos de saída são:

- `0`: senha encontrada;
- `1`: wordlist terminou sem encontrar a senha;
- `2`: entrada inválida ou erro controlado;
- `130`: interrupção pelo teclado (`Ctrl+C`).

## Exemplo pronto para execução

O diretório `exemplos/` contém um cenário completo para validar a aplicação:

- `arquivo_teste.zip`: arquivo protegido com criptografia AES-256;
- `wordlist.txt`: lista com 20 possíveis senhas;
- senha correta para conferência: `CyberSeguranca2026!`.

Na raiz do projeto, ative o ambiente virtual e execute:

```powershell
.\.venv\Scripts\Activate.ps1
zip-breaker ".\exemplos\arquivo_teste.zip" ".\exemplos\wordlist.txt"
```

A aplicação deve encontrar a senha na 16ª tentativa. Para validar também a
extração do conteúdo:

```powershell
zip-breaker ".\exemplos\arquivo_teste.zip" ".\exemplos\wordlist.txt" --extrair-para ".\exemplos\recuperado"
```

Após a execução, o arquivo `mensagem_teste.txt` estará dentro de
`exemplos/recuperado/`.

## Testes

A suíte usa `unittest`, incluído no Python:

```powershell
python -m unittest discover -s tests -v
```

## Integração com uma GUI

Exemplo mínimo da API independente de interface:

```python
from zip_breaker import CrackControl, Wordlist, ZipPasswordCracker

wordlist = Wordlist("senhas.txt")
control = CrackControl()
cracker = ZipPasswordCracker("arquivo.zip", progress_interval=50)

resultado = cracker.crack(
    wordlist,
    total=wordlist.count(),
    on_progress=lambda evento: print(evento.percentage),
    control=control,
)

# Em callbacks de botões da GUI:
# control.pause()
# control.resume()
# control.cancel()
```

Em uma GUI, execute `cracker.crack` em uma thread de trabalho para não bloquear a
janela; envie os eventos de progresso à thread principal conforme as regras do
framework gráfico escolhido.

## Organização

```text
src/zip_breaker/
├── archive.py      # leitura, teste de senha e extração segura
├── cli.py          # interface de terminal
├── control.py      # pausa/cancelamento para CLI ou GUI
├── cracker.py      # caso de uso de recuperação por wordlist
├── exceptions.py   # erros de domínio
├── models.py       # resultados e eventos imutáveis
└── wordlist.py     # leitura validada e em fluxo
tests/              # testes unitários e de integração local
```

## Limitações deliberadas

Este é um ataque de dicionário: ele só encontra a senha se ela estiver na
wordlist. Senhas fortes e ausentes da lista não são “descriptografadas”. O
programa assume a configuração usual em que todos os membros protegidos do ZIP
usam a mesma senha e valida um membro protegido completo (CRC no ZipCrypto e
autenticação HMAC no AES).
