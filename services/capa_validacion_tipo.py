"""
Capa de validación específica de tipo de documento
Valida que el documento corresponde al tipo esperado y extrae los datos
"""

import logging
import os
from typing import Any, Dict, Callable

from models.document_models import ProcessingStatus, FinalDecision
from utils.logging_utils import set_stage

logger = logging.getLogger(__name__)


def ejecutar_validacion_tipo_especifico(
    context: Dict[str, Any],
    document_type_name: str,
    document_types_collection: Any,
    ai_service: Any,
    update_processing_status: Callable[[Any, ProcessingStatus], None],
) -> Dict[str, Any]:
    """
    Valida que el documento corresponde al tipo específico esperado y extrae los datos.
    No clasifica, solo valida que sea el tipo correcto.
    
    Args:
        context: Contexto del procesamiento
        document_type_name: Nombre del tipo de documento esperado
        document_types_collection: Colección de tipos de documentos
        ai_service: Servicio de IA
        update_processing_status: Función para actualizar el estado
        
    Returns:
        Contexto actualizado con los resultados de validación y extracción
    """
    processed_doc = context["processed_doc"]
    ocr_text = context["ocr_text"]
    
    try:
        # Actualizar estado
        set_stage("validation")
        update_processing_status(processed_doc["_id"], ProcessingStatus.VALIDATION)
        
        # Obtener solo el tipo de documento específico
        document_type = document_types_collection.find_one({
            "name": document_type_name,
            "is_active": True
        })
        
        if not document_type:
            context["final_decision"] = FinalDecision.REJECTED
            context["rejection_reasons"].append(
                {
                    "reason": "Tipo de documento no configurado",
                    "document_type": document_type_name,
                }
            )
            context["processing_log"].append(
                f"Tipo de documento '{document_type_name}' no está configurado o no está activo"
            )
            logger.error(
                f"Tipo de documento '{document_type_name}' no encontrado en la base de datos "
                f"para documento {processed_doc['document_id']}"
            )
            return context
        
        # Validar y extraer en una sola llamada (optimización)
        # Usar método combinado si está disponible, sino usar métodos separados
        use_combined = os.getenv("USE_COMBINED_VALIDATION_EXTRACTION", "true").lower() == "true"
        has_method = hasattr(ai_service, 'verify_and_extract_document')
        
        logger.info(f"Configuración método combinado: use_combined={use_combined}, has_method={has_method} para documento {processed_doc['document_id']}")
        
        # Forzar uso del método combinado si está disponible (optimización activa por defecto)
        if use_combined and has_method:
            logger.info(f"Usando método combinado de validación y extracción para documento {processed_doc['document_id']}")
            # Método optimizado: validación y extracción en una sola llamada
            combined_result, combined_cost = ai_service.verify_and_extract_document(
                ocr_text, document_type_name, document_type
            )
            
            context["total_cost"] += combined_cost
            context["processing_log"].append(f"Validación y extracción combinadas completadas. Costo: ${combined_cost:.6f}")
            
            # Verificar si el documento corresponde al tipo esperado
            if not combined_result.get("is_correct_type", False):
                context["final_decision"] = FinalDecision.REJECTED
                context["rejection_reasons"].append(
                    {
                        "reason": "El documento no corresponde al tipo esperado",
                        "expected_type": document_type_name,
                        "ai_reason": combined_result.get("reason"),
                    }
                )
                context["processing_log"].append(
                    f"Documento rechazado: {combined_result.get('reason')}"
                )
                logger.warning(
                    f"Documento {processed_doc['document_id']} no corresponde al tipo esperado '{document_type_name}': "
                    f"{combined_result.get('reason')}"
                )
                return context
            
            # Si la validación es correcta, usar los datos extraídos
            extracted_data = combined_result.get("extracted_data") or {}
            context["extracted_data"] = extracted_data
            context["document_type_config"] = document_type
            context["document_type_id"] = document_type["_id"]
            context["document_type_name"] = document_type["name"]
            context["processing_log"].append("Extracción de datos completada (método combinado)")
            
            if not extracted_data or len(extracted_data) == 0:
                logger.warning(f"No se pudieron extraer datos del documento {processed_doc['document_id']}")
                context["processing_log"].append("Advertencia: No se pudieron extraer datos del documento")
        else:
            # Método tradicional: validación y extracción separadas
            logger.info(f"Usando método tradicional (separado) para documento {processed_doc['document_id']}")
            validation_result, validation_cost = ai_service.verify_document_type(
                ocr_text, document_type_name, document_type
            )
            
            context["total_cost"] += validation_cost
            context["processing_log"].append(f"Validación de tipo completada. Costo: ${validation_cost:.6f}")
            
            # Verificar si el documento corresponde al tipo esperado
            if not validation_result.get("is_correct_type", False):
                context["final_decision"] = FinalDecision.REJECTED
                context["rejection_reasons"].append(
                    {
                        "reason": "El documento no corresponde al tipo esperado",
                        "expected_type": document_type_name,
                        "ai_reason": validation_result.get("reason"),
                    }
                )
                context["processing_log"].append(
                    f"Documento rechazado: {validation_result.get('reason')}"
                )
                logger.warning(
                    f"Documento {processed_doc['document_id']} no corresponde al tipo esperado '{document_type_name}': "
                    f"{validation_result.get('reason')}"
                )
                return context
            
            # Si la validación es correcta, extraer los datos
            _procesar_extraccion(
                context=context,
                document_type=document_type,
                ai_service=ai_service,
                ocr_text=ocr_text,
                doc_id=processed_doc["document_id"],
            )
        
        logger.info(f"Validación y extracción completadas para documento {processed_doc['document_id']}")
        return context
        
    except Exception as e:
        set_stage("validation_error")
        logger.error(f"Error en validación de tipo: {e}")
        context["processing_log"].append(f"Error en validación de tipo: {str(e)}")
        raise


def _procesar_extraccion(
    context: Dict[str, Any],
    document_type: Dict[str, Any],
    ai_service: Any,
    ocr_text: str,
    doc_id: str,
) -> None:
    """Procesa la extracción de datos del documento"""
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

