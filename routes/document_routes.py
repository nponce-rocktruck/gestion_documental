"""
Rutas para consulta de documentos procesados
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, status

from models.document_models import ProcessingStatus
from database.mongodb_connection import get_collection

logger = logging.getLogger(__name__)

# Crear router
router = APIRouter(prefix="/api/v1", tags=["documents"])


@router.get("/documents/{document_id}/status")
async def get_document_status(document_id: str) -> Dict[str, Any]:
    """Obtiene el estado de procesamiento de un documento"""
    
    try:
        document = get_collection("OCR_processed_documents").find_one({
            "document_id": document_id
        })
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Documento {document_id} no encontrado"
            )
        
        return {
            "document_id": document_id,
            "status": document["processing_status"],
            "final_decision": document.get("final_decision"),
            "created_at": document["created_at"],
            "updated_at": document["updated_at"],
            "processed_at": document.get("processed_at")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al consultar estado del documento {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )


@router.get("/documents/{document_id}/result")
async def get_document_result(document_id: str) -> Dict[str, Any]:
    """Obtiene el resultado completo de procesamiento de un documento"""
    
    try:
        document = get_collection("OCR_processed_documents").find_one({
            "document_id": document_id
        })
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Documento {document_id} no encontrado"
            )
        
        if document["processing_status"] != ProcessingStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_202_ACCEPTED,
                detail="El documento aún está siendo procesado"
            )
        
        return {
            "document_id": document_id,
            "status": document["final_decision"],
            "extracted_data": document.get("extracted_data"),
            "validation_results": document.get("validation_results"),
            "rejection_reasons": document.get("rejection_reasons"),
            "processing_cost_usd": document.get("processing_cost_usd", 0.0),
            "processing_log": document.get("processing_log", []),
            "document_type": document.get("document_type_name"),
            "processed_at": document.get("processed_at")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al consultar resultado del documento {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )
