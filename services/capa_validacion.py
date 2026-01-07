import logging
from typing import Any, Dict, Callable, List

from models.document_models import ProcessingStatus
from utils.logging_utils import set_stage

logger = logging.getLogger(__name__)


def ejecutar_capa_validacion(
    context: Dict[str, Any],
    ai_service: Any,
    update_processing_status: Callable[[Any, ProcessingStatus], None],
) -> Dict[str, Any]:
    """
    Ejecuta la capa de validación (reglas generales y validación cruzada).
    Si hay un documento descargado del portal, también valida sus reglas.
    """
    processed_doc = context["processed_doc"]
    extracted_data = context["extracted_data"]
    user_data = processed_doc.get("user_data")
    document_type_config = context["document_type_config"]

    try:
        set_stage("validation")
        update_processing_status(processed_doc["_id"], ProcessingStatus.VALIDATION)

        validation_results: List[Dict[str, Any]] = []

        # Validar reglas del documento original
        if document_type_config.get("general_rules"):
            validation_results.extend(
                _validar_reglas_generales(
                    context=context,
                    ai_service=ai_service,
                    extracted_data=extracted_data,
                    document_type_config=document_type_config,
                    document_source="original",  # Marcar origen
                )
            )

        if document_type_config.get("validation_rules") and user_data:
            validation_results.extend(
                _validar_reglas_cruzadas(
                    context=context,
                    ai_service=ai_service,
                    extracted_data=extracted_data,
                    user_data=user_data,
                    document_type_config=document_type_config,
                    document_source="original",  # Marcar origen
                )
            )
        elif user_data and not document_type_config.get("validation_rules"):
            validation_results.extend(
                _validacion_dinamica(
                    context=context, 
                    ai_service=ai_service, 
                    extracted_data=extracted_data, 
                    user_data=user_data,
                    document_source="original"  # Marcar origen
                )
            )

        # Si hay documento descargado del portal, también validar sus reglas
        download_info = context.get("download_info")
        extracted_data_downloaded = None
        if download_info:
            extracted_data_downloaded = download_info.get("extracted_data_downloaded")
        
        if extracted_data_downloaded and document_type_config:
            logger.info("Validando reglas del documento descargado del portal")
            
            # Validar reglas generales del documento descargado
            if document_type_config.get("general_rules"):
                validation_results.extend(
                    _validar_reglas_generales(
                        context=context,
                        ai_service=ai_service,
                        extracted_data=extracted_data_downloaded,
                        document_type_config=document_type_config,
                        document_source="downloaded",  # Marcar origen
                    )
                )
            
            # Validar reglas cruzadas del documento descargado
            if document_type_config.get("validation_rules") and user_data:
                validation_results.extend(
                    _validar_reglas_cruzadas(
                        context=context,
                        ai_service=ai_service,
                        extracted_data=extracted_data_downloaded,
                        user_data=user_data,
                        document_type_config=document_type_config,
                        document_source="downloaded",  # Marcar origen
                    )
                )
            elif user_data and not document_type_config.get("validation_rules"):
                validation_results.extend(
                    _validacion_dinamica(
                        context=context,
                        ai_service=ai_service,
                        extracted_data=extracted_data_downloaded,
                        user_data=user_data,
                        document_source="downloaded"  # Marcar origen
                    )
                )

        context["validation_results"] = validation_results

        logger.info(f"Validación completada para documento {processed_doc['document_id']}")
        return context

    except Exception as e:
        set_stage("validation_error")
        logger.error(f"Error en validación: {e}")
        context["processing_log"].append(f"Error en validación: {str(e)}")
        raise


def _validar_reglas_generales(
    context: Dict[str, Any],
    ai_service: Any,
    extracted_data: Dict[str, Any],
    document_type_config: Dict[str, Any],
    document_source: str = "original",
) -> List[Dict[str, Any]]:
    general_rules_result, general_cost = ai_service.validate_general_rules(
        extracted_data, document_type_config["general_rules"], document_type_config["name"]
    )

    context["total_cost"] += general_cost
    general_validations = general_rules_result.get("validaciones_detalladas", [])
    
    # Agregar información del origen del documento a cada validación
    for validation in general_validations:
        validation["document_source"] = document_source
    
    context["processing_log"].append(
        f"Validación de reglas generales completada ({document_source}). Costo: ${general_cost:.6f}"
    )

    failed_general = [v for v in general_validations if v.get("resultado") != "APROBADO"]
    if failed_general:
        context["rejection_reasons"].extend(
            [
                {
                    "reason": "Regla general fallida",
                    "rule": v.get("nombre_regla"),
                    "details": v.get("razon"),
                    "type": "general",
                    "document_source": document_source,  # Marcar origen
                }
                for v in failed_general
            ]
        )

    return general_validations


def _validar_reglas_cruzadas(
    context: Dict[str, Any],
    ai_service: Any,
    extracted_data: Dict[str, Any],
    user_data: Dict[str, Any],
    document_type_config: Dict[str, Any],
    document_source: str = "original",
) -> List[Dict[str, Any]]:
    validation_rules_result, validation_cost = ai_service.validate_cross_validation_rules(
        extracted_data, user_data, document_type_config["validation_rules"], document_type_config["name"]
    )

    context["total_cost"] += validation_cost
    cross_validations = validation_rules_result.get("validaciones_detalladas", [])
    
    # Agregar información del origen del documento a cada validación
    for validation in cross_validations:
        validation["document_source"] = document_source
    
    context["processing_log"].append(
        f"Validación cruzada completada ({document_source}). Costo: ${validation_cost:.6f}"
    )

    failed_cross = [v for v in cross_validations if v.get("resultado") != "APROBADO"]
    if failed_cross:
        context["rejection_reasons"].extend(
            [
                {
                    "reason": "Validación cruzada fallida",
                    "rule": v.get("nombre_regla"),
                    "details": v.get("razon"),
                    "type": "cross_validation",
                    "document_source": document_source,  # Marcar origen
                }
                for v in failed_cross
            ]
        )

    return cross_validations


def _validacion_dinamica(
    context: Dict[str, Any],
    ai_service: Any,
    extracted_data: Dict[str, Any],
    user_data: Dict[str, Any],
    document_source: str = "original",
) -> List[Dict[str, Any]]:
    dynamic_validation_result, dynamic_cost = ai_service.dynamic_user_data_validation(extracted_data, user_data)

    context["total_cost"] += dynamic_cost
    dynamic_validations = dynamic_validation_result.get("validaciones_cruzadas", [])
    
    # Agregar información del origen del documento a cada validación
    for validation in dynamic_validations:
        validation["document_source"] = document_source
    
    context["processing_log"].append(
        f"Validación dinámica completada ({document_source}). Costo: ${dynamic_cost:.6f}"
    )

    campos_faltantes = dynamic_validation_result.get("campos_faltantes", [])
    if campos_faltantes:
        context["rejection_reasons"].append(
            {
                "reason": "Campos del usuario no encontrados en documento",
                "campos_faltantes": campos_faltantes,
                "type": "missing_fields",
                "document_source": document_source,  # Marcar origen
            }
        )

    return dynamic_validations

