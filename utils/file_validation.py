import os
from urllib.parse import urlparse

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".tif"}


def extract_filename_from_url(file_url: str) -> str:
    """Obtiene el nombre de archivo a partir de una URL."""
    parsed = urlparse(file_url)
    path = parsed.path or ""
    filename = os.path.basename(path)
    return filename or "documento_sin_nombre"


def validate_supported_extension(filename_or_url: str) -> str:
    """
    Valida que el archivo tenga una extensión soportada y la devuelve.
    Si la URL no tiene extensión visible, permite la validación (el tipo se determinará al descargar).
    """
    _, ext = os.path.splitext(filename_or_url.lower())
    
    # Si no hay extensión en la URL, permitirla (se validará al descargar por contenido)
    if not ext:
        return ""
    
    # Si hay extensión, validar que esté en la lista permitida
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Extensión de archivo no soportada: '{ext}'. "
            f"Solo se permiten: {', '.join(sorted(ALLOWED_EXTENSIONS))}."
        )
    return ext

