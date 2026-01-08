"""
Cliente HTTP para comunicarse con el servicio de verificación en la VM
"""

import logging
import requests
from typing import Dict, Any, Optional
import os

logger = logging.getLogger(__name__)


class VMVerificationClient:
    """Cliente para llamar al servicio de verificación en la VM"""
    
    def __init__(self, vm_url: Optional[str] = None):
        """
        Inicializa el cliente
        
        Args:
            vm_url: URL base de la VM (ej: http://34.176.102.209:8080)
                   Si es None, lee de variable de entorno VM_VERIFICATION_URL
        """
        self.vm_url = vm_url or os.getenv("VM_VERIFICATION_URL", "http://34.176.102.209:8080")
        self.vm_url = self.vm_url.rstrip("/")
        self.timeout = int(os.getenv("VM_REQUEST_TIMEOUT", "120"))
    
    def _make_request(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Realiza una petición HTTP a la VM
        
        Args:
            endpoint: Endpoint a llamar (ej: /verificar/portal-documental)
            data: Datos a enviar en el body
        
        Returns:
            Dict con la respuesta
        
        Raises:
            Exception: Si hay error en la petición
        """
        url = f"{self.vm_url}{endpoint}"
        
        try:
            logger.info(f"Llamando a VM: {url}")
            response = requests.post(
                url,
                json=data,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            logger.error(f"Timeout al llamar a VM: {url}")
            raise Exception(f"Timeout al comunicarse con la VM después de {self.timeout} segundos")
        except requests.exceptions.ConnectionError:
            logger.error(f"Error de conexión con VM: {url}")
            raise Exception("No se pudo conectar con la VM. Verifica que esté ejecutándose.")
        except requests.exceptions.HTTPError as e:
            logger.error(f"Error HTTP al llamar a VM: {e}")
            try:
                error_detail = response.json().get("detail", str(e))
            except:
                error_detail = str(e)
            raise Exception(f"Error en VM: {error_detail}")
        except Exception as e:
            logger.error(f"Error inesperado al llamar a VM: {e}")
            raise Exception(f"Error al comunicarse con la VM: {str(e)}")
    
    def verificar_portal_documental(self, codigo: str, timeout: int = 90) -> Dict[str, Any]:
        """
        Verifica un código en el portal documental de la DT
        
        Args:
            codigo: Código de verificación (formato: "XXXX XXXX XXXX")
            timeout: Tiempo máximo de espera en segundos
        
        Returns:
            Dict con el resultado de la verificación
        """
        return self._make_request(
            "/verificar/portal-documental",
            {
                "codigo": codigo,
                "timeout": timeout
            }
        )
    
    def verificar_persona_natural(
        self,
        folio_oficina: str,
        folio_anio: str,
        folio_numero: str,
        codigo_verificacion: str,
        timeout: int = 90
    ) -> Dict[str, Any]:
        """
        Verifica y descarga certificado F30 de Persona Natural
        
        Args:
            folio_oficina: Folio oficina (ej: "1234")
            folio_anio: Folio año (ej: "2024")
            folio_numero: Folio número (ej: "5678")
            codigo_verificacion: Código de verificación
            timeout: Tiempo máximo de espera en segundos
        
        Returns:
            Dict con el resultado de la verificación
        """
        return self._make_request(
            "/verificar/persona-natural",
            {
                "folio_oficina": folio_oficina,
                "folio_anio": folio_anio,
                "folio_numero": folio_numero,
                "codigo_verificacion": codigo_verificacion,
                "timeout": timeout
            }
        )
    
    def health_check(self) -> bool:
        """
        Verifica si la VM está disponible
        
        Returns:
            True si está disponible, False en caso contrario
        """
        try:
            url = f"{self.vm_url}/health"
            response = requests.get(url, timeout=5)
            return response.status_code == 200
        except:
            return False

