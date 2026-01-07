"""
Modelos específicos para cada tipo de documento
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from utils.file_validation import validate_supported_extension, ALLOWED_EXTENSIONS
import os


class BaseDocumentRequest(BaseModel):
    """Modelo base para solicitudes de procesamiento"""
    document_id: str = Field(..., description="ID único del documento")
    file_url: str = Field(..., description="URL del archivo")
    origin: str = Field(..., description="Origen de la solicitud")
    destination: str = Field(..., description="Destino de la respuesta")
    response_url: Optional[str] = Field(default=None, description="URL para enviar la respuesta")

    @field_validator("file_url")
    @classmethod
    def ensure_supported_extension(cls, value: str) -> str:
        validate_supported_extension(value)
        return value


class EtiquetaWalmartRequest(BaseDocumentRequest):
    """Modelo para solicitudes de procesamiento de Etiqueta de Envío Walmart"""
    
    @field_validator("file_url")
    @classmethod
    def validate_file_type(cls, value: str) -> str:
        """Valida que el archivo sea PDF o imagen"""
        _, ext = os.path.splitext(value.lower())
        if ext and ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"Etiqueta Walmart solo acepta: PDF, JPG, JPEG, PNG, TIFF")
        return value


class EtiquetaEnviameRequest(BaseDocumentRequest):
    """Modelo para solicitudes de procesamiento de Etiqueta de Envío ENVIAME"""
    
    @field_validator("file_url")
    @classmethod
    def validate_file_type(cls, value: str) -> str:
        """Valida que el archivo sea PDF o imagen"""
        _, ext = os.path.splitext(value.lower())
        if ext and ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"Etiqueta ENVIAME solo acepta: PDF, JPG, JPEG, PNG, TIFF")
        return value


class CertificadoF30Request(BaseDocumentRequest):
    """Modelo para solicitudes de procesamiento de Certificado F30"""
    user_data: Dict[str, Any] = Field(..., description="Datos del usuario para validación (obligatorio para F30)")
    tipo_f30: str = Field(..., description="Tipo de F30: 'persona_natural' o 'razon_social'")
    
    @field_validator("file_url")
    @classmethod
    def validate_file_type(cls, value: str) -> str:
        """Valida que el archivo sea solo PDF"""
        _, ext = os.path.splitext(value.lower())
        if ext != ".pdf":
            raise ValueError("Certificado F30 solo acepta archivos PDF")
        return value
    
    @field_validator("tipo_f30")
    @classmethod
    def validate_tipo_f30(cls, value: str) -> str:
        """Valida que el tipo de F30 sea válido"""
        if value not in ["persona_natural", "razon_social"]:
            raise ValueError("tipo_f30 debe ser 'persona_natural' o 'razon_social'")
        return value

