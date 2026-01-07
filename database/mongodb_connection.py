"""
Configuración de conexión a MongoDB para la API de Documentos
"""

import os
from typing import Optional
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import logging

logger = logging.getLogger(__name__)


class MongoDBConnection:
    """Clase para manejar la conexión a MongoDB"""
    
    def __init__(self):
        self._client: Optional[MongoClient] = None
        self._async_client: Optional[AsyncIOMotorClient] = None
        self._database: Optional[Database] = None
        self._async_database: Optional[AsyncIOMotorDatabase] = None
    
    def get_connection_string(self) -> str:
        """Obtiene la cadena de conexión a MongoDB desde variables de entorno"""
        # Obtener URL de MongoDB de variables de entorno (OBLIGATORIO en producción)
        mongodb_url = os.getenv("MONGODB_URL", "").strip()
        database_name = os.getenv("MONGODB_DATABASE", "Rocktruck").strip()
        
        # En producción (Cloud Run), MONGODB_URL DEBE estar configurada
        if not mongodb_url:
            error_msg = "❌ MONGODB_URL no configurada. Debe establecerse como variable de entorno en Cloud Run."
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Validar que la URL tenga el formato correcto
        if not mongodb_url.startswith(("mongodb://", "mongodb+srv://")):
            logger.error(f"❌ URL de MongoDB inválida: {mongodb_url}")
            raise ValueError(f"URL de MongoDB debe comenzar con 'mongodb://' o 'mongodb+srv://': {mongodb_url}")
        
        # Para producción con credenciales separadas (alternativa a MONGODB_URL)
        # Solo usar si MONGODB_URL no está configurada
        if os.getenv("MONGODB_USER") and os.getenv("MONGODB_PASSWORD") and not mongodb_url:
            username = os.getenv("MONGODB_USER")
            password = os.getenv("MONGODB_PASSWORD")
            host = os.getenv("MONGODB_HOST")
            port = os.getenv("MONGODB_PORT", "27017")
            
            if not host:
                raise ValueError("MONGODB_HOST debe estar configurado si se usan MONGODB_USER y MONGODB_PASSWORD")
            
            mongodb_url = f"mongodb://{username}:{password}@{host}:{port}"
        
        # Construir URL completa
        # Si la URL ya termina con /, no agregar otro
        if mongodb_url.endswith("/"):
            connection_string = f"{mongodb_url}{database_name}"
        else:
            connection_string = f"{mongodb_url}/{database_name}"
        
        logger.info(f"🔗 URL de conexión MongoDB: {connection_string.split('@')[0]}@.../{database_name}")
        return connection_string
    
    def connect(self) -> Database:
        """Establece conexión síncrona a MongoDB"""
        if self._database is None:
            connection_string = self.get_connection_string()
            # Usar serverSelectionTimeoutMS para evitar bloqueos durante el inicio
            # La conexión se establecerá de forma lazy cuando se necesite
            self._client = MongoClient(
                connection_string,
                serverSelectionTimeoutMS=5000,  # 5 segundos máximo para seleccionar servidor
                connectTimeoutMS=5000,  # 5 segundos máximo para conectar
                socketTimeoutMS=30000  # 30 segundos para operaciones
            )
            database_name = os.getenv("MONGODB_DATABASE", "Rocktruck")
            self._database = self._client[database_name]
            # No verificar la conexión aquí - se hará de forma lazy
            logger.info(f"Cliente MongoDB inicializado para: {database_name}")
        return self._database
    
    async def connect_async(self) -> AsyncIOMotorDatabase:
        """Establece conexión asíncrona a MongoDB"""
        if self._async_database is None:
            connection_string = self.get_connection_string()
            # Usar timeouts para evitar bloqueos durante el inicio
            self._async_client = AsyncIOMotorClient(
                connection_string,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                socketTimeoutMS=30000
            )
            database_name = os.getenv("MONGODB_DATABASE", "Rocktruck")
            self._async_database = self._async_client[database_name]
            # No verificar la conexión aquí - se hará de forma lazy
            logger.info(f"Cliente MongoDB (async) inicializado para: {database_name}")
        return self._async_database
    
    def get_collection(self, collection_name: str) -> Collection:
        """Obtiene una colección específica"""
        if self._database is None:
            self.connect()
        return self._database[collection_name]
    
    async def get_async_collection(self, collection_name: str):
        """Obtiene una colección específica de forma asíncrona"""
        if self._async_database is None:
            await self.connect_async()
        return self._async_database[collection_name]
    
    def close(self):
        """Cierra la conexión síncrona"""
        if self._client:
            self._client.close()
            self._client = None
            self._database = None
    
    async def close_async(self):
        """Cierra la conexión asíncrona"""
        if self._async_client:
            self._async_client.close()
            self._async_client = None
            self._async_database = None


# Instancia global de la conexión
mongodb_connection = MongoDBConnection()


def get_database() -> Database:
    """Función helper para obtener la base de datos"""
    return mongodb_connection.connect()


def get_collection(collection_name: str) -> Collection:
    """Función helper para obtener una colección"""
    return mongodb_connection.get_collection(collection_name)


async def get_async_database():
    """Función helper para obtener la base de datos de forma asíncrona"""
    return await mongodb_connection.connect_async()


async def get_async_collection(collection_name: str):
    """Función helper para obtener una colección de forma asíncrona"""
    return await mongodb_connection.get_async_collection(collection_name)
