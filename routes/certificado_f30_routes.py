"""
Rutas para procesamiento de Certificado F30 - Antecedentes Laborales y Previsionales
"""

import logging
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks, status

from models.document_type_models import CertificadoF30Request
from services.document_processors.certificado_f30_processor import CertificadoF30Processor
from database.mongodb_connection import get_collection
from utils.file_validation import extract_filename_from_url
from utils.logging_utils import document_logging_context, set_stage
from models.document_models import ProcessingStatus, FinalDecision

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["certificado-f30"])

# Inicializar procesador de forma lazy
_f30_processor = None

def get_f30_processor():
    """Obtiene la instancia del procesador (lazy initialization)"""
    global _f30_processor
    if _f30_processor is None:
        _f30_processor = CertificadoF30Processor()
    return _f30_processor


@router.post("/certificado_f30", response_model=Dict[str, Any])
async def process_certificado_f30(
    request: CertificadoF30Request,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Endpoint para procesar un Certificado F30 - Antecedentes Laborales y Previsionales
    
    Acepta solo archivos PDF.
    Requiere datos del usuario (user_data) para validación cruzada.
    """
    
    doc_id = request.document_id
    
    with document_logging_context(
        doc_id=doc_id,
        provided_classification="Certificado F30 - Antecedentes Laborales y Previsionales",
        stage="ingest"
    ):
        try:
            logger.info(f"Recibida solicitud de procesamiento para Certificado F30 {doc_id}")
            
            # Validar que el documento no esté ya siendo procesado
            existing_doc = get_collection("OCR_processed_documents").find_one({
                "document_id": doc_id
            })
            
            if existing_doc:
                if existing_doc["processing_status"] in [ProcessingStatus.PENDING, ProcessingStatus.OCR, ProcessingStatus.CLASSIFICATION, ProcessingStatus.VALIDATION]:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"El documento {doc_id} ya está siendo procesado"
                    )
            
            # Preparar datos del documento
            document_data = {
                "document_id": doc_id,
                "file_url": request.file_url,
                "file_name": extract_filename_from_url(request.file_url),
                "origin": request.origin,
                "destination": request.destination,
                "user_data": request.user_data,  # F30 requiere user_data obligatorio
                "tipo_f30": request.tipo_f30,  # Tipo de F30: persona_natural o razon_social
                "response_url": request.response_url
            }
            
            # Procesar documento en background
            set_stage("queued")
            background_tasks.add_task(process_document_background, document_data, "f30")
            
            return {
                "message": "Certificado F30 recibido para procesamiento",
                "document_id": doc_id,
                "status": "PROCESSING",
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error al procesar solicitud: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error interno del servidor: {str(e)}"
            )


async def process_document_background(document_data: Dict[str, Any], processor_type: str):
    """Procesa el documento en background y envía el resultado"""
    
    document_id = document_data["document_id"]
    
    with document_logging_context(
        doc_id=document_id,
        provided_classification="Certificado F30 - Antecedentes Laborales y Previsionales",
        stage="background_start"
    ):
        try:
            logger.info(f"Iniciando procesamiento en background para documento {document_id}")
            
            # Procesar documento
            set_stage("processing")
            processor = get_f30_processor()
            result = processor.process_document(document_data)
            
            # Preparar respuesta
            response_data = {
                "document_id": document_id,
                "status": result.get("final_decision", FinalDecision.MANUAL_REVIEW),
                "extracted_data": result.get("extracted_data"),
                "validation_results": result.get("validation_results"),
                "rejection_reasons": result.get("rejection_reasons"),
                "processing_cost_usd": result.get("total_cost", 0.0),
                "processing_log": result.get("processing_log", []),
                "processed_at": datetime.utcnow().isoformat()
            }
            
            # Enviar resultado a la URL de respuesta si está configurada
            if document_data.get("response_url"):
                await send_result_to_url(document_data["response_url"], response_data)
            
            set_stage("completed")
            logger.info(f"Procesamiento completado para documento {document_id}")
            
        except Exception as e:
            set_stage("error")
            logger.error(f"Error en procesamiento background para documento {document_id}: {e}")
            
            # Enviar error a la URL de respuesta si está configurada
            if document_data.get("response_url"):
                error_response = {
                    "document_id": document_id,
                    "status": "ERROR",
                    "error": str(e),
                    "processed_at": datetime.utcnow().isoformat()
                }
                await send_result_to_url(document_data["response_url"], error_response)


async def send_result_to_url(url: str, data: Dict[str, Any]):
    """Envía el resultado a la URL especificada"""
    
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data) as response:
                if response.status == 200:
                    logger.info(f"Resultado enviado exitosamente a {url}")
                else:
                    logger.error(f"Error al enviar resultado a {url}: {response.status}")
    except Exception as e:
        logger.error(f"Error al enviar resultado a {url}: {e}")

