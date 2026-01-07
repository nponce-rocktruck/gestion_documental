"""
Modelos de MongoDB para la API de Documentos
Basado en la estructura del proyecto ia_orchestrator pero adaptado para MongoDB
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, field_validator
from bson import ObjectId
from pymongo import MongoClient

from utils.file_validation import validate_supported_extension


class ProcessingStatus(str, Enum):
    """Estados del procesamiento de documentos"""
    PENDING = "PENDING"
    OCR = "OCR"
    CLASSIFICATION = "CLASSIFICATION"
    VALIDATION = "VALIDATION"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class FinalDecision(str, Enum):
    """Decisiones finales del procesamiento"""
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    MANUAL_REVIEW = "MANUAL_REVIEW"


class CountryEnum(str, Enum):
    """Países soportados"""
    CL = "CL"
    VE = "VE"
    CO = "CO"


class DocumentType(BaseModel):
    """Modelo para tipos de documentos en MongoDB"""
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )
    
    id: Optional[ObjectId] = Field(default_factory=ObjectId, alias="_id")
    name: str = Field(..., max_length=100)
    country: CountryEnum = Field(default=CountryEnum.CL)
    description: Optional[str] = None
    extraction_schema: Dict[str, Any] = Field(..., description="Schema JSON para extracción de datos")
    general_rules: Optional[List[Dict[str, Any]]] = Field(default=None, description="Reglas generales que no requieren datos del usuario")
    validation_rules: Optional[List[Dict[str, Any]]] = Field(default=None, description="Reglas de validación cruzada con datos del usuario")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ProcessedDocument(BaseModel):
    """Modelo para documentos procesados en MongoDB"""
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )
    
    id: Optional[ObjectId] = Field(default_factory=ObjectId, alias="_id")
    
    # Identificadores del documento
    document_id: str = Field(..., description="ID único del documento")
    file_url: str = Field(..., description="URL del archivo")
    file_name: str = Field(..., description="Nombre del archivo")
    
    # Información del usuario/cliente
    #owner_user_name: Optional[str] = Field(default=None, description="Nombre del usuario propietario")
    origin: str = Field(..., description="Origen de la solicitud")
    destination: str = Field(..., description="Destino de la respuesta")
    
    # Clasificación previa
    provided_classification: str = Field(..., description="Clasificación proporcionada por el usuario")
    
    # Datos del usuario para validación cruzada
    user_data: Optional[Dict[str, Any]] = Field(default=None, description="Datos del usuario para validación")
    
    # Estado del procesamiento
    processing_status: ProcessingStatus = Field(default=ProcessingStatus.PENDING)
    final_decision: Optional[FinalDecision] = Field(default=None)
    
    # Resultados del procesamiento
    ocr_text: Optional[str] = Field(default=None, description="Texto extraído por OCR")
    extracted_data: Optional[Dict[str, Any]] = Field(default=None, description="Datos extraídos del documento")
    classification_result: Optional[Dict[str, Any]] = Field(default=None, description="Resultado de la clasificación")
    
    # Información del tipo de documento
    document_type_id: Optional[ObjectId] = Field(default=None, description="ID del tipo de documento identificado")
    document_type_name: Optional[str] = Field(default=None, description="Nombre del tipo de documento")
    
    # Validaciones y reglas
    validation_results: Optional[List[Dict[str, Any]]] = Field(default=None, description="Resultados de validaciones")
    rejection_reasons: Optional[List[Dict[str, Any]]] = Field(default=None, description="Razones de rechazo")
    
    # Costos y métricas
    processing_cost_usd: float = Field(default=0.0, description="Costo total del procesamiento en USD")
    processing_log: List[str] = Field(default_factory=list, description="Log del procesamiento")
    
    # URLs de respuesta
    response_url: Optional[str] = Field(default=None, description="URL para enviar la respuesta")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = Field(default=None, description="Fecha de finalización del procesamiento")


class ProcessingRequest(BaseModel):
    """Modelo para solicitudes de procesamiento"""
    document_id: str = Field(..., description="ID único del documento")
    file_url: str = Field(..., description="URL del archivo")
    origin: str = Field(..., description="Origen de la solicitud")
    destination: str = Field(..., description="Destino de la respuesta")
    provided_classification: str = Field(..., description="Clasificación proporcionada por el usuario")
    user_data: Optional[Dict[str, Any]] = Field(default=None, description="Datos del usuario para validación")
    response_url: Optional[str] = Field(default=None, description="URL para enviar la respuesta")

    @field_validator("file_url")
    @classmethod
    def ensure_supported_extension(cls, value: str) -> str:
        validate_supported_extension(value)
        return value


class ProcessingResponse(BaseModel):
    """Modelo para respuestas de procesamiento"""
    document_id: str
    status: ProcessingStatus
    final_decision: Optional[FinalDecision] = None
    extracted_data: Optional[Dict[str, Any]] = None
    validation_results: Optional[List[Dict[str, Any]]] = None
    rejection_reasons: Optional[List[Dict[str, Any]]] = None
    processing_cost_usd: float = 0.0
    processing_log: List[str] = []
    processed_at: Optional[datetime] = None


class DocumentTypeCreate(BaseModel):
    """Modelo para crear tipos de documentos"""
    name: str = Field(..., max_length=100)
    country: CountryEnum = Field(default=CountryEnum.CL)
    description: Optional[str] = None
    extraction_schema: Dict[str, Any] = Field(..., description="Schema JSON para extracción de datos")
    general_rules: Optional[List[Dict[str, Any]]] = Field(default=None, description="Reglas generales que no requieren datos del usuario")
    validation_rules: Optional[List[Dict[str, Any]]] = Field(default=None, description="Reglas de validación cruzada con datos del usuario")
    is_active: bool = Field(default=True)


class DocumentTypeUpdate(BaseModel):
    """Modelo para actualizar tipos de documentos"""
    name: Optional[str] = Field(None, max_length=100)
    country: Optional[CountryEnum] = None
    description: Optional[str] = None
    extraction_schema: Optional[Dict[str, Any]] = None
    general_rules: Optional[List[Dict[str, Any]]] = None
    validation_rules: Optional[List[Dict[str, Any]]] = None
    is_active: Optional[bool] = None
