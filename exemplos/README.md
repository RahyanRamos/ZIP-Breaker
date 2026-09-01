# Exemplo para teste ponta a ponta

O arquivo `arquivo_teste.zip` usa criptografia AES-256 e contém o arquivo
`mensagem_teste.txt`.

- Wordlist: `wordlist.txt`
- Senha conhecida para conferência: `CyberSeguranca2026!`

Na raiz do projeto, execute:

```powershell
.\.venv\Scripts\Activate.ps1
zip-breaker ".\exemplos\arquivo_teste.zip" ".\exemplos\wordlist.txt"
```

Para testar também a extração:

```powershell
zip-breaker ".\exemplos\arquivo_teste.zip" ".\exemplos\wordlist.txt" --extrair-para ".\exemplos\recuperado"
```
