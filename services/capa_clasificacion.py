import logging
from typing import Any, Dict, Callable, Iterable

from models.document_models import ProcessingStatus, FinalDecision
from utils.logging_utils import set_stage

logger = logging.getLogger(__name__)


def ejecutar_capa_clasificacion(
    context: Dict[str, Any],
    document_types_collection: Any,
    ai_service: Any,
    update_processing_status: Callable[[Any, ProcessingStatus], None],
) -> Dict[str, Any]:
    """
    Ejecuta la capa de verificación de clasificación y extracción de datos.
    """
    processed_doc = context["processed_doc"]
    ocr_text = context["ocr_text"]
    provided_classification = processed_doc["provided_classification"]

    try:
        # Actualizar estado
        set_stage("classification")
        update_processing_status(processed_doc["_id"], ProcessingStatus.CLASSIFICATION)

        # Obtener tipos de documentos disponibles
        available_types = list(document_types_collection.find({"is_active": True}))

        # Verificar clasificación con IA
        classification_result, ai_cost = ai_service.verify_document_classification(
            ocr_text, provided_classification, available_types
        )

        context["total_cost"] += ai_cost
        context["classification_result"] = classification_result
        context["processing_log"].append(f"Verificación de clasificación completada. Costo: ${ai_cost:.6f}")

        # Verificar si la clasificación es correcta
        if not classification_result.get("is_correct", False):
            context["final_decision"] = FinalDecision.REJECTED
            context["rejection_reasons"].append(
                {
                    "reason": "Clasificación incorrecta",
                    "provided": provided_classification,
                    "suggested": classification_result.get("suggested_type"),
                    "ai_reason": classification_result.get("reason"),
                }
            )
            context["processing_log"].append(f"Clasificación rechazada: {classification_result.get('reason')}")
            logger.warning(
                f"Clasificación incorrecta para documento {processed_doc['document_id']}: "
                f"{classification_result.get('reason')}"
            )
            return context

        # Buscar el tipo de documento en la base de datos
        document_type_name = classification_result.get("document_type")
        document_type = document_types_collection.find_one({"name": document_type_name})

        if not document_type:
            context["final_decision"] = FinalDecision.REJECTED
            context["rejection_reasons"].append(
                {
                    "reason": "Tipo de documento no configurado",
                    "document_type": document_type_name,
                }
            )
            context["processing_log"].append(
                f"Tipo de documento '{document_type_name}' no está configurado"
            )
            logger.error(
                f"Tipo de documento '{document_type_name}' no encontrado en la base de datos "
                f"para documento {processed_doc['document_id']}"
            )
            return context

        _procesar_extraccion(
            context=context,
            document_type=document_type,
            ai_service=ai_service,
            ocr_text=ocr_text,
            doc_id=processed_doc["document_id"],
        )

        logger.info(f"Clasificación y extracción completadas para documento {processed_doc['document_id']}")
        return context

    except Exception as e:
        set_stage("classification_error")
        logger.error(f"Error en clasificación: {e}")
        context["processing_log"].append(f"Error en clasificación: {str(e)}")
        raise


def _procesar_extraccion(
    context: Dict[str, Any],
    document_type: Dict[str, Any],
    ai_service: Any,
    ocr_text: str,
    doc_id: str,
) -> None:
    try:
        extracted_data, extraction_cost = ai_service.extract_data_with_schema(
            ocr_text, document_type["extraction_schema"]
        )

        context["total_cost"] += extraction_cost
        context["extracted_data"] = extracted_data
        context["document_type_config"] = document_type
        context["document_type_id"] = document_type["_id"]
        context["document_type_name"] = document_type["name"]
        context["processing_log"].append(f"Extracción de datos completada. Costo: ${extraction_cost:.6f}")

        if not extracted_data or len(extracted_data) == 0:
            logger.warning(f"No se pudieron extraer datos del documento {doc_id}")
            context["processing_log"].append("Advertencia: No se pudieron extraer datos del documento")

    except Exception as e:
        logger.error(f"Error en extracción de datos para documento {doc_id}: {e}")
        context["processing_log"].append(f"Error en extracción de datos: {str(e)}")
        context["extracted_data"] = {}
        context["document_type_config"] = document_type
        context["document_type_id"] = document_type["_id"]
        context["document_type_name"] = document_type["name"]

