"""Exceções de domínio exibíveis de forma amigável pela CLI ou por uma GUI."""


class ZipBreakerError(Exception):
    """Erro esperado e tratável da aplicação."""


class InputFileError(ZipBreakerError):
    """Um arquivo de entrada não existe, não é legível ou é inválido."""


class InvalidArchiveError(InputFileError):
    """O arquivo informado não é um ZIP válido ou está corrompido."""


class ArchiveNotEncryptedError(InputFileError):
    """O ZIP não possui nenhum arquivo protegido por senha."""


class EmptyWordlistError(InputFileError):
    """A wordlist não contém nenhuma senha utilizável."""


class WordlistEncodingError(InputFileError):
    """A wordlist não pôde ser lida com a codificação solicitada."""


class UnsupportedEncryptionError(ZipBreakerError):
    """O método de criptografia do ZIP não é suportado pelo ambiente."""


class ArchiveReadError(ZipBreakerError):
    """Falha de leitura não causada simplesmente por uma senha incorreta."""


class UnsafeArchiveError(ZipBreakerError):
    """O ZIP contém um caminho inseguro e não deve ser extraído."""

