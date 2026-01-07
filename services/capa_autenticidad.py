import logging
import os
from copy import deepcopy
from io import BytesIO
from typing import Any, Dict, Iterable, List, Optional

import requests

try:
    from PIL import Image, ExifTags  # type: ignore
except Exception:  # pragma: no cover
    Image = None  # type: ignore
    ExifTags = None  # type: ignore

from utils.file_validation import ALLOWED_EXTENSIONS, validate_supported_extension
from utils.logging_utils import set_stage

logger = logging.getLogger(__name__)

DEFAULT_MIN_FILE_SIZE_KB = 10
DEFAULT_FORBIDDEN_SOFTWARE = (
    "photoshop",
    "gimp",
    "canva",
    "pixlr",
    "fotor",
)
DEFAULT_PDF_EDITORS = (
    "adobe acrobat",
    "foxit",
    "nitro",
    "pdfelement",
    "pdfsam",
    "smallpdf",
    "ilovepdf",
    "lovepdf",
    "sejda",
    "pdfescape",
    "libreoffice",
    "openoffice",
    "microsoft word",
    "microsoft edge",
    "google docs",
    "chrome pdf viewer",
    #"skia/pdf",
    "pdf-xchange",
    "bluebeam",
    "bluebeam revu",
    "pdf studio",
    "masterpdf",
    "scribus",
    "docusign",
    "hellosign",
    "pandadoc",
    "kami",
)
DEFAULT_AUTHENTICITY_CHECKS = {
    "http_headers": {"enabled": True, "min_size_kb": DEFAULT_MIN_FILE_SIZE_KB},
    "image_metadata": {"enabled": True, "forbidden_software": list(DEFAULT_FORBIDDEN_SOFTWARE)},
    "pdf_metadata": {"enabled": True, "flag_editors": True, "editors": list(DEFAULT_PDF_EDITORS)},
}
DEFAULT_AUTHENTICITY_CONFIG = {
    "enabled": True,
    "checks": DEFAULT_AUTHENTICITY_CHECKS,
}


def ejecutar_capa_autenticidad(
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Ejecuta verificaciones básicas de autenticidad sobre el archivo original.

    Busca señales de manipulación analizando cabeceras HTTP, metadatos EXIF para imágenes
    y patrones comunes en PDFs. Registra advertencias y puede marcar el documento como sospechoso.
    """
    processed_doc = context["processed_doc"]
    
    # Usar configuración por defecto
    merged_config = DEFAULT_AUTHENTICITY_CONFIG

    if not merged_config.get("enabled", True):
        logger.info("Capa de autenticidad deshabilitada por configuración.")
        context["processing_log"].append("Capa de autenticidad omitida: deshabilitada en configuración.")
        context["authenticity_result"] = "SKIPPED"
        context["authenticity_signals"] = []
        return context

    processed_doc = context["processed_doc"]
    file_url: Optional[str] = processed_doc.get("file_url")
    file_name: str = processed_doc.get("file_name") or "documento_sin_nombre"

    if not file_url:
        logger.warning("Capa de autenticidad omitida: no hay file_url disponible.")
        return context

    try:
        validate_supported_extension(file_name)
    except ValueError as exc:
        # Si no hay extensión, permitir continuar (se validará al procesar el contenido)
        _, ext = os.path.splitext(file_name.lower())
        if not ext:
            logger.info(f"Archivo sin extensión visible: {file_name}. Se validará por contenido.")
        else:
            logger.error(f"Archivo con extensión no soportada: {file_name}. {exc}")
            raise

    set_stage("authenticity")
    logger.info(f"Iniciando verificación de autenticidad para documento {processed_doc['document_id']}")

    signals: List[str] = []
    severity = "PASSED"

    checks_config = merged_config.get("checks", {})

    try:
        http_headers_cfg = checks_config.get("http_headers", {})
        if http_headers_cfg.get("enabled", True):
            consistencia = _verificar_consistencia_archivo(
                file_url,
                file_name,
                min_size_kb=http_headers_cfg.get("min_size_kb"),
            )
            signals.extend(consistencia["signals"])
            severity = _combinar_severidad(severity, consistencia["result"])

        extension = os.path.splitext(file_name)[1].lower()
        if extension in ALLOWED_EXTENSIONS - {".pdf"}:
            image_cfg = checks_config.get("image_metadata", {})
            if image_cfg.get("enabled", True):
                metadata = _analizar_metadatos_imagen(
                    file_url,
                    forbidden_tools=image_cfg.get("forbidden_software"),
                )
                signals.extend(metadata["signals"])
                severity = _combinar_severidad(severity, metadata["result"])
        elif extension == ".pdf":
            pdf_cfg = checks_config.get("pdf_metadata", {})
            if pdf_cfg.get("enabled", True):
                metadata = _analizar_metadatos_pdf(
                    file_url,
                    flag_editors=pdf_cfg.get("flag_editors", True),
                    editors=pdf_cfg.get("editors"),
                )
                signals.extend(metadata["signals"])
                severity = _combinar_severidad(severity, metadata["result"])

    except Exception as exc:  # pragma: no cover - última línea de defensa
        logger.error(f"Error inesperado en capa de autenticidad: {exc}")
        signals.append("authenticity_unexpected_error")
        severity = "FAILED"

    if severity in ("WARNING", "FAILED"):
        context["rejection_reasons"].append(
            {
                "reason": "Sospecha de manipulación del documento",
                "details": {"severidad": severity, "signals": signals},
                "type": "authenticity",
            }
        )

    context["authenticity_result"] = severity
    context["authenticity_signals"] = signals
    context["processing_log"].append(
        f"Verificación de autenticidad completada. Resultado: {severity}. Señales: {signals or 'ninguna'}."
    )

    return context


def _verificar_consistencia_archivo(
    file_url: str, file_name: str, *, min_size_kb: Optional[int] = None
) -> Dict[str, Any]:
    signals: List[str] = []
    severity = "PASSED"

    try:
        response = requests.head(file_url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning(f"No se pudo obtener cabeceras del archivo: {exc}")
        return {"result": "WARNING", "signals": ["head_request_failed"]}

    content_type = response.headers.get("content-type", "").lower()
    size_header = response.headers.get("content-length")
    extension = os.path.splitext(file_name)[1].lower()

    expected_types = {
        ".pdf": ["application/pdf"],
        ".jpg": ["image/jpeg"],
        ".jpeg": ["image/jpeg"],
        ".png": ["image/png"],
        ".tiff": ["image/tiff"],
        ".tif": ["image/tiff"],
    }

    if extension in expected_types and content_type not in expected_types[extension]:
        signals.append(f"mime_mismatch:{extension}:{content_type or 'unknown'}")
        severity = _combinar_severidad(severity, "WARNING")

    if size_header:
        try:
            size_kb = int(size_header) / 1024
            min_expected = min_size_kb if min_size_kb is not None else DEFAULT_MIN_FILE_SIZE_KB
            if size_kb < min_expected:  # menos de tamaño esperado
                signals.append(f"suspicious_file_size:{size_kb:.2f}KB")
                severity = _combinar_severidad(severity, "WARNING")
        except ValueError:
            logger.debug("No se pudo interpretar content-length como entero.")

    return {"result": severity, "signals": signals}


def _analizar_metadatos_imagen(
    file_url: str,
    forbidden_tools: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    if Image is None or ExifTags is None:
        logger.debug("Pillow no disponible; omitiendo análisis EXIF.")
        return {"result": "NOT_APPLICABLE", "signals": ["exif_not_available"]}

    try:
        response = requests.get(file_url, timeout=15)
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning(f"No se pudo descargar imagen para análisis EXIF: {exc}")
        return {"result": "WARNING", "signals": ["image_download_failed"]}

    signals: List[str] = []
    severity = "PASSED"

    try:
        data = response.content
        with Image.open(BytesIO(data)) as img:
            exif_data = img.getexif()
    except Exception as exc:
        logger.warning(f"No se pudo leer EXIF de la imagen: {exc}")
        return {"result": "WARNING", "signals": ["exif_parse_error"]}

    if not exif_data:
        return {"result": "WARNING", "signals": ["no_exif_data"]}

    try:
        exif = {ExifTags.TAGS.get(tag, str(tag)): value for tag, value in exif_data.items()}
    except Exception:
        exif = {}

    software = str(exif.get("Software", "")).lower()
    base_tools = forbidden_tools or DEFAULT_FORBIDDEN_SOFTWARE
    tools_to_check = tuple(str(tool).lower() for tool in base_tools)
    if any(tool in software for tool in tools_to_check):
        signals.append(f"editing_software_detected:{software or 'desconocido'}")
        severity = _combinar_severidad(severity, "WARNING")

    if exif.get("DateTime") and exif.get("DateTimeOriginal") and exif["DateTime"] != exif["DateTimeOriginal"]:
        signals.append("exif_inconsistent_timestamps")
        severity = _combinar_severidad(severity, "WARNING")

    gps_info = exif.get("GPSInfo")
    if gps_info and len(gps_info) < 2:
        signals.append("incomplete_gps_info")
        severity = _combinar_severidad(severity, "WARNING")

    return {"result": severity, "signals": signals}


def _analizar_metadatos_pdf(
    file_url: str,
    *,
    flag_editors: bool = True,
    editors: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    try:
        response = requests.get(file_url, timeout=15)
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning(f"No se pudo descargar PDF para análisis de metadatos: {exc}")
        return {"result": "WARNING", "signals": ["pdf_download_failed"]}

    try:
        content = response.content.decode("utf-8", errors="ignore")
    except Exception:
        content = ""

    signals: List[str] = []
    severity = "PASSED"

    lowered = content.lower()
    if flag_editors:
        pdf_editors = tuple(str(editor).lower() for editor in (editors or DEFAULT_PDF_EDITORS))
        for editor in pdf_editors:
            if editor in lowered:
                signals.append(f"pdf_editor_detected:{editor}")
                severity = _combinar_severidad(severity, "WARNING")

    if "annotations" in lowered or "comments" in lowered:
        signals.append("pdf_contains_annotations")
        severity = _combinar_severidad(severity, "WARNING")

    return {"result": severity, "signals": signals}


def _combinar_severidad(actual: str, nueva: str) -> str:
    niveles = {"NOT_APPLICABLE": 0, "PASSED": 1, "WARNING": 2, "FAILED": 3}
    if nueva not in niveles:
        return actual
    return actual if niveles[actual] >= niveles[nueva] else nueva


def _merge_dicts(base: Dict[str, Any], override: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Mezcla recursivamente diccionarios sin mutar los originales.
    """
    result = deepcopy(base)
    if not override:
        return result

    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge_dicts(result[key], value)
        else:
            result[key] = value
    return result

