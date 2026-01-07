"""
Rutas de salud y monitoreo
"""

import logging
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, status
from database.mongodb_connection import get_collection

logger = logging.getLogger(__name__)

# Crear router
router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Endpoint de salud de la API"""
    
    try:
        # Verificar conexión a MongoDB (no bloquear si falla)
        db_status = "unknown"
        db_error = None
        try:
            get_collection("OCR_document_types").find_one()
            db_status = "healthy"
        except Exception as e:
            db_status = "unhealthy"
            db_error = str(e)
            logger.warning(f"Error de conexión a MongoDB (no crítico): {e}")
        
        # La API siempre devuelve healthy, incluso si DB está down
        response = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "database": db_status,
            "services": {
                "api": "healthy",
                "database": db_status
            }
        }
        
        if db_error:
            response["database_error"] = db_error
        
        return response
        
    except Exception as e:
        logger.error(f"Error en health check: {e}")
        # En caso de error crítico, devolver degraded pero no fallar
        return {
            "status": "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "error": str(e)
        }


@router.get("/")
async def root() -> Dict[str, Any]:
    """Endpoint raíz"""
    
    return {
        "message": "API de Documentos",
        "version": "1.0.0",
        "description": "API para procesamiento de documentos con IA",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health"
    }


@router.get("/stats")
async def get_api_stats() -> Dict[str, Any]:
    """Obtiene estadísticas de la API"""
    
    try:
        # Contar documentos procesados
        total_documents = get_collection("OCR_processed_documents").count_documents({})
        
        # Contar por estado
        pending_documents = get_collection("OCR_processed_documents").count_documents({
            "processing_status": "PENDING"
        })
        
        completed_documents = get_collection("OCR_processed_documents").count_documents({
            "processing_status": "COMPLETED"
        })
        
        failed_documents = get_collection("OCR_processed_documents").count_documents({
            "processing_status": "FAILED"
        })
        
        # Contar por decisión final
        approved_documents = get_collection("OCR_processed_documents").count_documents({
            "final_decision": "APPROVED"
        })
        
        rejected_documents = get_collection("OCR_processed_documents").count_documents({
            "final_decision": "REJECTED"
        })
        
        # Contar tipos de documentos
        total_document_types = get_collection("OCR_document_types").count_documents({
            "is_active": True
        })
        
        return {
            "total_documents": total_documents,
            "documents_by_status": {
                "pending": pending_documents,
                "completed": completed_documents,
                "failed": failed_documents
            },
            "documents_by_decision": {
                "approved": approved_documents,
                "rejected": rejected_documents
            },
            "total_document_types": total_document_types,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error al obtener estadísticas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )


@router.get("/metrics")
async def get_metrics() -> Dict[str, Any]:
    """Obtiene métricas detalladas de la API"""
    
    try:
        # Métricas de procesamiento
        pipeline = [
            {
                "$group": {
                    "_id": None,
                    "total_cost": {"$sum": "$processing_cost_usd"},
                    "avg_cost": {"$avg": "$processing_cost_usd"},
                    "total_processing_time": {"$sum": "$processing_time_seconds"}
                }
            }
        ]
        
        cost_metrics = list(get_collection("OCR_processed_documents").aggregate(pipeline))
        
        # Métricas por tipo de documento
        type_metrics = list(get_collection("OCR_processed_documents").aggregate([
            {
                "$group": {
                    "_id": "$document_type_name",
                    "count": {"$sum": 1},
                    "avg_cost": {"$avg": "$processing_cost_usd"}
                }
            },
            {"$sort": {"count": -1}}
        ]))
        
        return {
            "cost_metrics": cost_metrics[0] if cost_metrics else {
                "total_cost": 0,
                "avg_cost": 0,
                "total_processing_time": 0
            },
            "type_metrics": type_metrics,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error al obtener métricas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )
