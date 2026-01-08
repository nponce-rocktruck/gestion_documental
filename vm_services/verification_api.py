"""
API de Verificación para Máquina Virtual
Expone endpoints para verificaciones que requieren IP de Sudamérica
"""

import logging
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.verificacion_dt.portal_verification_service import PortalVerificationService
from services.verificacion_dt.persona_natural_verification_service import PersonaNaturalVerificationService

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="VM Verification API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directorio de descargas
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", str(Path(__file__).parent.parent / "downloads"))
Path(DOWNLOAD_DIR).mkdir(parents=True, exist_ok=True)


# Modelos de request
class PortalVerificationRequest(BaseModel):
    codigo: str
    timeout: Optional[int] = 90


class PersonaNaturalVerificationRequest(BaseModel):
    folio_oficina: str
    folio_anio: str
    folio_numero: str
    codigo_verificacion: str
    timeout: Optional[int] = 90


# Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "vm-verification-api"}


@app.post("/verificar/portal-documental")
async def verificar_portal_documental(request: PortalVerificationRequest):
    """
    Verifica un código en el portal documental de la DT
    https://midt.dirtrab.cl/verificadorDocumental
    """
    def _ejecutar_verificacion():
        """Ejecuta la verificación en un thread separado para evitar conflicto con asyncio"""
        service = PortalVerificationService(
            headless=True,
            download_dir=DOWNLOAD_DIR
        )
        return service.verify_code(
            codigo=request.codigo,
            timeout=request.timeout
        )
    
    try:
        logger.info(f"Verificando código en portal documental: {request.codigo}")
        
        # Ejecutar en thread separado para evitar conflicto con asyncio
        loop = None
        try:
            import asyncio
            loop = asyncio.get_event_loop()
        except:
            pass
        
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_ejecutar_verificacion)
            result = future.result(timeout=request.timeout + 30)  # Timeout adicional para seguridad
        
        # Convertir Path a string si existe downloaded_file
        if result.get("downloaded_file"):
            result["downloaded_file"] = str(result["downloaded_file"])
        
        return result
        
    except Exception as e:
        logger.error(f"Error en verificación portal documental: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/verificar/persona-natural")
async def verificar_persona_natural(request: PersonaNaturalVerificationRequest):
    """
    Verifica y descarga certificado F30 de Persona Natural
    http://tramites.dt.gob.cl/tramitesenlinea/VerificadorTramites/VerificadorTramites.aspx
    """
    def _ejecutar_verificacion():
        """Ejecuta la verificación en un thread separado para evitar conflicto con asyncio"""
        service = PersonaNaturalVerificationService(
            headless=True,
            download_dir=DOWNLOAD_DIR
        )
        return service.verify_and_download(
            folio_oficina=request.folio_oficina,
            folio_anio=request.folio_anio,
            folio_numero=request.folio_numero,
            codigo_verificacion=request.codigo_verificacion,
            timeout=request.timeout
        )
    
    try:
        logger.info(f"Verificando persona natural - Folio: {request.folio_oficina}-{request.folio_anio}-{request.folio_numero}")
        
        # Ejecutar en thread separado para evitar conflicto con asyncio
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_ejecutar_verificacion)
            result = future.result(timeout=request.timeout + 30)  # Timeout adicional para seguridad
        
        # Convertir Path a string si existe downloaded_file
        if result.get("downloaded_file"):
            result["downloaded_file"] = str(result["downloaded_file"])
        
        return result
        
    except Exception as e:
        logger.error(f"Error en verificación persona natural: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)

