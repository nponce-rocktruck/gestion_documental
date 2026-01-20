"""
Cliente HTTP para API de verificación en VM
"""

import os
import logging
import base64
import tempfile
from typing import Dict, Any, Optional
from pathlib import Path

import requests

logger = logging.getLogger(__name__)


class VMVerificationClient:
    """Cliente para llamar a la API de verificación en la VM"""
    
    def __init__(self, vm_url: Optional[str] = None, timeout: int = 180):
        """
        Inicializa el cliente
        
        Args:
            vm_url: URL base de la API en la VM (ej: http://34.176.102.209:8080)
            timeout: Timeout en segundos para las peticiones
        """
        self.vm_url = vm_url or os.getenv("VM_VERIFICATION_URL", "http://34.176.102.209:8080")
        self.timeout = timeout
        self.base_url = self.vm_url.rstrip("/")
        
    def _save_base64_to_file(self, pdf_base64: str, document_id: str, prefix: str = "certificado") -> Optional[str]:
        """
        Guarda PDF desde base64 a archivo temporal
        
        Args:
            pdf_base64: PDF en base64
            document_id: ID del documento para el nombre del archivo
            prefix: Prefijo para el nombre del archivo
            
        Returns:
            Ruta del archivo guardado o None si hay error
        """
        try:
            # Crear directorio temporal si no existe
            download_dir = Path(os.getenv("F30_DOWNLOAD_DIR", "downloads/f30"))
            download_dir.mkdir(parents=True, exist_ok=True)
            
            # Decodificar base64
            pdf_bytes = base64.b64decode(pdf_base64)
            
            # Generar nombre de archivo
            import time
            timestamp = int(time.time())
            filename = f"{prefix}_{document_id}_{timestamp}.pdf"
            file_path = download_dir / filename
            
            # Guardar archivo
            with open(file_path, "wb") as f:
                f.write(pdf_bytes)
            
            logger.info(f"PDF guardado desde base64: {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Error al guardar PDF desde base64: {e}", exc_info=True)
            return None
    
    def verificar_portal_documental(
        self,
        codigo: str,
        document_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verifica código en portal documental
        
        Args:
            codigo: Código de verificación (formato: "XXXX XXXX XXXX")
            document_id: ID del documento (opcional, para nombre de archivo)
            
        Returns:
            Dict con:
            - success: bool
            - valid: bool
            - message: str
            - downloaded_file: Optional[str] - Ruta del archivo si se descargó
            - error: Optional[str]
        """
        try:
            logger.info(f"Verificando código en VM: {codigo}")
            
            url = f"{self.base_url}/verificar/portal-documental"
            payload = {"codigo": codigo}
            
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            
            result = response.json()
            
            # Si hay PDF en base64, guardarlo como archivo
            downloaded_file = None
            if result.get("pdf_base64"):
                doc_id = document_id or codigo.replace(" ", "")
                downloaded_file = self._save_base64_to_file(
                    result["pdf_base64"],
                    doc_id,
                    prefix="portal_documental"
                )
            
            # Convertir respuesta de VM a formato esperado por el procesador
            return {
                "success": result.get("success", False),
                "valid": result.get("valid", False),
                "message": result.get("message", ""),
                "downloaded_file": downloaded_file,
                "error": result.get("error"),
                "error_message": result.get("error_message"),
                "portal_message": result.get("error_message")
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error en petición a VM: {e}", exc_info=True)
            return {
                "success": False,
                "valid": False,
                "message": "Error al conectar con VM",
                "error": str(e),
                "downloaded_file": None
            }
        except Exception as e:
            logger.error(f"Error inesperado en verificación portal documental: {e}", exc_info=True)
            return {
                "success": False,
                "valid": False,
                "message": "Error durante la verificación",
                "error": str(e),
                "downloaded_file": None
            }
    
    def verificar_persona_natural(
        self,
        folio_oficina: str,
        folio_anio: str,
        folio_numero: str,
        codigo_verificacion: str,
        document_id: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Verifica y descarga certificado F30 para persona natural
        
        Args:
            folio_oficina: Folio oficina
            folio_anio: Folio año
            folio_numero: Folio número consecutivo
            codigo_verificacion: Código de verificación
            document_id: ID del documento (opcional)
            timeout: Timeout personalizado (opcional)
            
        Returns:
            Dict con:
            - success: bool
            - valid: bool
            - message: str
            - downloaded_file: Optional[str]
            - error: Optional[str]
            - folios_ingresados: Dict
        """
        try:
            logger.info(f"Verificando persona natural en VM: {folio_oficina}/{folio_anio}/{folio_numero}")
            
            url = f"{self.base_url}/verificar/persona-natural"
            payload = {
                "folio_oficina": folio_oficina,
                "folio_anio": folio_anio,
                "folio_numero": folio_numero,
                "codigo_verificacion": codigo_verificacion
            }
            
            req_timeout = timeout or self.timeout
            response = requests.post(url, json=payload, timeout=req_timeout)
            response.raise_for_status()
            
            result = response.json()
            
            # Si hay PDF en base64, guardarlo como archivo
            downloaded_file = None
            if result.get("pdf_base64"):
                doc_id = document_id or f"{folio_oficina}_{folio_anio}_{folio_numero}"
                downloaded_file = self._save_base64_to_file(
                    result["pdf_base64"],
                    doc_id,
                    prefix="f30_persona_natural"
                )
            
            # Convertir respuesta
            return {
                "success": result.get("success", False),
                "valid": result.get("valid", False),
                "message": result.get("message", ""),
                "downloaded_file": downloaded_file,
                "error": result.get("error"),
                "error_message": result.get("error_message"),
                "portal_message": result.get("error_message"),
                "folios_ingresados": {
                    "folio_oficina": folio_oficina,
                    "folio_anio": folio_anio,
                    "folio_numero_consecutivo": folio_numero,
                    "codigo_verificacion": codigo_verificacion
                }
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error en petición a VM: {e}", exc_info=True)
            return {
                "success": False,
                "valid": False,
                "message": "Error al conectar con VM",
                "error": str(e),
                "downloaded_file": None,
                "folios_ingresados": {
                    "folio_oficina": folio_oficina,
                    "folio_anio": folio_anio,
                    "folio_numero_consecutivo": folio_numero,
                    "codigo_verificacion": codigo_verificacion
                }
            }
        except Exception as e:
            logger.error(f"Error inesperado en verificación persona natural: {e}", exc_info=True)
            return {
                "success": False,
                "valid": False,
                "message": "Error durante la verificación",
                "error": str(e),
                "downloaded_file": None,
                "folios_ingresados": {
                    "folio_oficina": folio_oficina,
                    "folio_anio": folio_anio,
                    "folio_numero_consecutivo": folio_numero,
                    "codigo_verificacion": codigo_verificacion
                }
            }

