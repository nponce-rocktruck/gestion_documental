"""
Servicio para subir archivos a Google Cloud Storage
"""

import logging
import os
import time
from typing import Dict, Any, Optional
from pathlib import Path
from google.cloud import storage
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class StorageService:
    """Servicio para subir archivos a Google Cloud Storage"""
    
    def __init__(self, bucket_name: Optional[str] = None):
        """
        Inicializa el servicio de almacenamiento
        
        Args:
            bucket_name: Nombre del bucket. Si no se proporciona, se usa la variable de entorno
        """
        self.bucket_name = bucket_name or os.getenv("GCS_BUCKET_NAME", "documents-bucket-01")
        
        # Inicializar cliente de Google Cloud Storage
        try:
            self.storage_client = storage.Client()
            logger.info(f"Cliente de Google Cloud Storage inicializado. Bucket: {self.bucket_name}")
        except Exception as e:
            logger.error(f"Error al inicializar cliente de Google Cloud Storage: {e}")
            raise
    
    def upload_file_to_bucket(
        self,
        file_path: str,
        bucket_path: Optional[str] = None,
        mime_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sube un archivo desde el sistema de archivos local a Google Cloud Storage
        
        Args:
            file_path: Ruta local del archivo a subir
            bucket_path: Ruta donde quedará en el bucket (opcional, se genera automáticamente si no se proporciona)
            mime_type: Tipo MIME del archivo (opcional, se detecta automáticamente si no se proporciona)
        
        Returns:
            Dict con:
            - success: bool - Si la subida fue exitosa
            - bucket_path: str - Ruta del archivo en el bucket
            - public_url: str - URL pública del archivo
            - error: Optional[str] - Mensaje de error si hubo problema
        """
        try:
            # Verificar que el archivo existe
            if not os.path.exists(file_path):
                return {
                    "success": False,
                    "error": f"El archivo no existe: {file_path}",
                    "bucket_path": None,
                    "public_url": None
                }
            
            # Obtener información del archivo
            file_path_obj = Path(file_path)
            file_name = file_path_obj.name
            file_size = file_path_obj.stat().st_size
            
            if file_size == 0:
                return {
                    "success": False,
                    "error": "El archivo está vacío",
                    "bucket_path": None,
                    "public_url": None
                }
            
            # Generar ruta en el bucket si no se proporciona
            if not bucket_path:
                timestamp = int(time.time() * 1000)
                environment = os.getenv("ENVIRONMENT", "dev")
                extension = file_path_obj.suffix or ".pdf"
                # Generar nombre único
                new_name = f"{file_path_obj.stem}_{timestamp}{extension}"
                bucket_path = f"{environment}/certificados_f30/{new_name}"
            
            # Detectar tipo MIME si no se proporciona
            if not mime_type:
                mime_type = self._detect_mime_type(file_path_obj.suffix)
            
            # Leer archivo
            with open(file_path, 'rb') as file:
                file_data = file.read()
            
            # Subir a Google Cloud Storage
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(bucket_path)
            
            blob.upload_from_string(
                file_data,
                content_type=mime_type
            )
            
            # Generar URL pública
            public_url = f"https://storage.googleapis.com/{self.bucket_name}/{bucket_path}"
            
            logger.info(f"Archivo subido exitosamente: {file_name} -> {bucket_path} ({file_size} bytes)")
            
            return {
                "success": True,
                "bucket_path": bucket_path,
                "public_url": public_url,
                "file_name": file_name,
                "file_size": file_size,
                "mime_type": mime_type,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Error al subir archivo a Google Cloud Storage: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "bucket_path": None,
                "public_url": None
            }
    
    def upload_buffer_to_bucket(
        self,
        buffer_data: bytes,
        filename: str,
        bucket_path: Optional[str] = None,
        mime_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sube un archivo desde memoria (buffer) a Google Cloud Storage
        
        Args:
            buffer_data: Datos del archivo en bytes
            filename: Nombre del archivo
            bucket_path: Ruta donde quedará en el bucket (opcional)
            mime_type: Tipo MIME del archivo (opcional)
        
        Returns:
            Dict con:
            - success: bool - Si la subida fue exitosa
            - bucket_path: str - Ruta del archivo en el bucket
            - public_url: str - URL pública del archivo
            - error: Optional[str] - Mensaje de error si hubo problema
        """
        try:
            if len(buffer_data) == 0:
                return {
                    "success": False,
                    "error": "El buffer está vacío",
                    "bucket_path": None,
                    "public_url": None
                }
            
            # Generar ruta en el bucket si no se proporciona
            if not bucket_path:
                timestamp = int(time.time() * 1000)
                environment = os.getenv("ENVIRONMENT", "dev")
                file_path_obj = Path(filename)
                extension = file_path_obj.suffix or ".pdf"
                new_name = f"{file_path_obj.stem}_{timestamp}{extension}"
                bucket_path = f"{environment}/certificados_f30/{new_name}"
            
            # Detectar tipo MIME si no se proporciona
            if not mime_type:
                file_path_obj = Path(filename)
                mime_type = self._detect_mime_type(file_path_obj.suffix)
            
            # Subir a Google Cloud Storage
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(bucket_path)
            
            blob.upload_from_string(
                buffer_data,
                content_type=mime_type
            )
            
            # Generar URL pública
            public_url = f"https://storage.googleapis.com/{self.bucket_name}/{bucket_path}"
            
            logger.info(f"Archivo subido exitosamente desde buffer: {filename} -> {bucket_path} ({len(buffer_data)} bytes)")
            
            return {
                "success": True,
                "bucket_path": bucket_path,
                "public_url": public_url,
                "file_name": filename,
                "file_size": len(buffer_data),
                "mime_type": mime_type,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Error al subir archivo desde buffer a Google Cloud Storage: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "bucket_path": None,
                "public_url": None
            }
    
    def _detect_mime_type(self, extension: str) -> str:
        """
        Detecta el tipo MIME basado en la extensión del archivo
        
        Args:
            extension: Extensión del archivo (ej: ".pdf", ".jpg")
        
        Returns:
            Tipo MIME del archivo
        """
        mime_types = {
            ".pdf": "application/pdf",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".bmp": "image/bmp",
            ".tiff": "image/tiff",
            ".tif": "image/tiff",
            ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".xls": "application/vnd.ms-excel",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }
        
        extension_lower = extension.lower()
        return mime_types.get(extension_lower, "application/octet-stream")

