import logging
from typing import Any, Dict, Callable, Tuple

from models.document_models import ProcessingStatus
from utils.logging_utils import set_stage

logger = logging.getLogger(__name__)


def ejecutar_capa_ocr(
    context: Dict[str, Any],
    ocr_service: Any,
    update_processing_status: Callable[[Any, ProcessingStatus], None],
) -> Dict[str, Any]:
    """
    Ejecuta la capa de OCR del pipeline.
    """
    processed_doc = context["processed_doc"]
    file_url = processed_doc["file_url"]

    try:
        # Actualizar estado
        set_stage("ocr")
        update_processing_status(processed_doc["_id"], ProcessingStatus.OCR)

        # Ejecutar OCR
        ocr_text, ocr_cost = _extraer_texto(ocr_service, file_url)

        # Actualizar contexto
        context["ocr_text"] = ocr_text
        context["total_cost"] += ocr_cost
        context["processing_log"].append(f"OCR completado. Costo: ${ocr_cost:.6f}")

        logger.info(f"OCR completado para documento {processed_doc['document_id']}")
        return context

    except Exception as e:
        set_stage("ocr_error")
        logger.error(f"Error en OCR: {e}")
        context["processing_log"].append(f"Error en OCR: {str(e)}")
        raise


def _extraer_texto(ocr_service: Any, file_url: str) -> Tuple[str, float]:
    """
    Extrae el texto del documento utilizando el servicio configurado.
    """
    return ocr_service.extract_text_from_url(file_url)

