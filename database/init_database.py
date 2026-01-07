"""
Script para inicializar la base de datos MongoDB con las colecciones necesarias
"""

import os
import sys
from datetime import datetime
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import CollectionInvalid
import logging

# Agregar el directorio raíz al path para importar modelos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.document_models import DocumentType, ProcessedDocument, CountryEnum

logger = logging.getLogger(__name__)


def verify_database_connection():
    """Verifica la conexión a la base de datos existente"""
    
    # Configuración de conexión desde variables de entorno (OBLIGATORIO en producción)
    mongodb_url = os.getenv("MONGODB_URL", "").strip()
    database_name = os.getenv("MONGODB_DATABASE", "Rocktruck").strip()
    
    # En producción (Cloud Run), MONGODB_URL DEBE estar configurada
    if not mongodb_url:
        error_msg = "❌ MONGODB_URL no configurada. Debe establecerse como variable de entorno en Cloud Run."
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Conectar a MongoDB con timeouts para evitar bloqueos durante el startup
    client = MongoClient(
        mongodb_url,
        serverSelectionTimeoutMS=5000,  # 5 segundos máximo para seleccionar servidor
        connectTimeoutMS=5000,  # 5 segundos máximo para conectar
        socketTimeoutMS=10000  # 10 segundos para operaciones
    )
    db = client[database_name]
    
    try:
        # Verificar que las colecciones existan (con timeout)
        collections = db.list_collection_names()
        
        required_collections = ["OCR_document_types", "OCR_processed_documents"]
        missing_collections = [col for col in required_collections if col not in collections]
        
        if missing_collections:
            raise Exception(f"Colecciones faltantes: {missing_collections}. Ejecuta los scripts de configuración primero.")
        
        # Verificar que haya tipos de documentos (con timeout)
        doc_types_count = db.OCR_document_types.count_documents({})
        if doc_types_count == 0:
            raise Exception("No hay tipos de documentos configurados. Ejecuta los scripts de configuración primero.")
        
        logger.info(f"Conexión a base de datos '{database_name}' verificada correctamente")
        logger.info(f"Colecciones encontradas: {collections}")
        logger.info(f"Tipos de documentos: {doc_types_count}")
        
    except Exception as e:
        logger.error(f"Error al verificar la base de datos: {e}")
        raise
    finally:
        client.close()



if __name__ == "__main__":
    # Configurar logging
    logging.basicConfig(level=logging.INFO)
    
    print("Verificando conexión a base de datos MongoDB...")
    verify_database_connection()
    print("✅ Base de datos verificada correctamente!")
    print("\nPara configurar la base de datos desde cero, ejecuta:")
    print("bash scripts/setup_database.sh")
