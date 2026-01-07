"""
Rutas para gestión de tipos de documentos
"""

import logging
from datetime import datetime
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, status
from bson import ObjectId

from models.document_models import DocumentType, DocumentTypeCreate, DocumentTypeUpdate
from database.mongodb_connection import get_collection

logger = logging.getLogger(__name__)

# Crear router
router = APIRouter(prefix="/api/v1", tags=["document-types"])


@router.get("/document-types", response_model=List[DocumentType])
async def get_document_types() -> List[DocumentType]:
    """Obtiene todos los tipos de documentos activos"""
    
    try:
        document_types = list(get_collection("OCR_document_types").find({"is_active": True}))
        return [DocumentType(**doc) for doc in document_types]
        
    except Exception as e:
        logger.error(f"Error al obtener tipos de documentos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )


@router.get("/document-types/{type_id}", response_model=DocumentType)
async def get_document_type(type_id: str) -> DocumentType:
    """Obtiene un tipo de documento específico por ID"""
    
    try:
        document_type = get_collection("OCR_document_types").find_one({"_id": ObjectId(type_id)})
        
        if not document_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tipo de documento {type_id} no encontrado"
            )
        
        return DocumentType(**document_type)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener tipo de documento {type_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )


@router.post("/document-types", response_model=DocumentType)
async def create_document_type(document_type: DocumentTypeCreate) -> DocumentType:
    """Crea un nuevo tipo de documento"""
    
    try:
        # Verificar que no exista un tipo con el mismo nombre
        existing = get_collection("OCR_document_types").find_one({"name": document_type.name})
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe un tipo de documento con el nombre '{document_type.name}'"
            )
        
        # Crear el tipo de documento
        document_type_data = document_type.dict()
        document_type_data["created_at"] = datetime.utcnow()
        document_type_data["updated_at"] = datetime.utcnow()
        
        result = get_collection("OCR_document_types").insert_one(document_type_data)
        document_type_data["_id"] = result.inserted_id
        
        return DocumentType(**document_type_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al crear tipo de documento: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )


@router.put("/document-types/{type_id}", response_model=DocumentType)
async def update_document_type(type_id: str, document_type: DocumentTypeUpdate) -> DocumentType:
    """Actualiza un tipo de documento existente"""
    
    try:
        # Verificar que el tipo existe
        existing = get_collection("OCR_document_types").find_one({"_id": ObjectId(type_id)})
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tipo de documento {type_id} no encontrado"
            )
        
        # Actualizar el tipo de documento
        update_data = {k: v for k, v in document_type.dict().items() if v is not None}
        update_data["updated_at"] = datetime.utcnow()
        
        get_collection("OCR_document_types").update_one(
            {"_id": ObjectId(type_id)},
            {"$set": update_data}
        )
        
        # Obtener el tipo actualizado
        updated = get_collection("OCR_document_types").find_one({"_id": ObjectId(type_id)})
        return DocumentType(**updated)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al actualizar tipo de documento: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )


@router.delete("/document-types/{type_id}")
async def delete_document_type(type_id: str) -> Dict[str, Any]:
    """Desactiva un tipo de documento (soft delete)"""
    
    try:
        # Verificar que el tipo existe
        existing = get_collection("OCR_document_types").find_one({"_id": ObjectId(type_id)})
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tipo de documento {type_id} no encontrado"
            )
        
        # Desactivar el tipo de documento
        get_collection("OCR_document_types").update_one(
            {"_id": ObjectId(type_id)},
            {
                "$set": {
                    "is_active": False,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return {
            "message": f"Tipo de documento {type_id} desactivado correctamente",
            "type_id": type_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al desactivar tipo de documento: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )


@router.get("/document-types/{type_id}/rules")
async def get_document_type_rules(type_id: str) -> Dict[str, Any]:
    """Obtiene las reglas de un tipo de documento específico"""
    
    try:
        document_type = get_collection("OCR_document_types").find_one({"_id": ObjectId(type_id)})
        
        if not document_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tipo de documento {type_id} no encontrado"
            )
        
        return {
            "type_id": type_id,
            "name": document_type["name"],
            "general_rules": document_type.get("general_rules", []),
            "validation_rules": document_type.get("validation_rules", []),
            "total_general_rules": len(document_type.get("general_rules", [])),
            "total_validation_rules": len(document_type.get("validation_rules", []))
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener reglas del tipo de documento {type_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )
