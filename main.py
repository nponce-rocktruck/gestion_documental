"""
API de Documentos - FastAPI
API abstraída para procesamiento de documentos con IA

Soporta dos modos de despliegue:
- Cloud Run: Usa uvicorn directamente (if __name__ == "__main__")
- Cloud Functions: Usa Vellox adapter (función handler)
"""

import os
import logging
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from utils.logging_utils import configure_logging

# Configurar logging PRIMERO para poder usarlo en las importaciones
configure_logging()

# Crear logger después de configurar logging
logger = logging.getLogger(__name__)

# Cargar variables de entorno desde .env solo si existe (para desarrollo local)
# En Cloud Run, las variables de entorno se pasan directamente, no desde .env
if os.path.exists(".env"):
    load_dotenv()
    logger.info("📄 Archivo .env encontrado, cargando variables locales")
else:
    logger.info("☁️  Ejecutándose en producción, usando variables de entorno de Cloud Run")
# Importar rutas (con manejo de errores - no bloquear inicio)
document_router = None
document_type_router = None
health_router = None
etiqueta_walmart_router = None
etiqueta_enviame_router = None
certificado_f30_router = None

# Almacenar errores de importación para diagnóstico
import_errors = {}

try:
    from routes.document_routes import router as document_router
    logger.info("✅ document_routes importado")
except Exception as e:
    import_errors["document_routes"] = str(e)
    logger.error(f"❌ Error importando document_routes: {e}", exc_info=True)

try:
    from routes.document_type_routes import router as document_type_router
    logger.info("✅ document_type_routes importado")
except Exception as e:
    import_errors["document_type_routes"] = str(e)
    logger.error(f"❌ Error importando document_type_routes: {e}", exc_info=True)

try:
    from routes.health_routes import router as health_router
    logger.info("✅ health_routes importado")
except Exception as e:
    import_errors["health_routes"] = str(e)
    logger.error(f"❌ Error importando health_routes: {e}", exc_info=True)

try:
    from routes.etiqueta_walmart_routes import router as etiqueta_walmart_router
    logger.info("✅ etiqueta_walmart_routes importado")
except Exception as e:
    import_errors["etiqueta_walmart_routes"] = str(e)
    logger.error(f"❌ Error importando etiqueta_walmart_routes: {e}", exc_info=True)
    import traceback
    logger.error(f"Traceback completo: {traceback.format_exc()}")

try:
    from routes.etiqueta_enviame_routes import router as etiqueta_enviame_router
    logger.info("✅ etiqueta_enviame_routes importado")
except Exception as e:
    import_errors["etiqueta_enviame_routes"] = str(e)
    logger.error(f"❌ Error importando etiqueta_enviame_routes: {e}", exc_info=True)

try:
    from routes.certificado_f30_routes import router as certificado_f30_router
    logger.info("✅ certificado_f30_routes importado")
except Exception as e:
    import_errors["certificado_f30_routes"] = str(e)
    logger.error(f"❌ Error importando certificado_f30_routes: {e}", exc_info=True)
    import traceback
    logger.error(f"Traceback completo: {traceback.format_exc()}")

# Importar verificación de base de datos
try:
    from database.init_database import verify_database_connection
    logger.info("✅ Verificación de DB importada correctamente")
except Exception as e:
    logger.warning(f"⚠️  Error importando verificación de DB: {e}")
    # Crear función dummy si no se puede importar
    def verify_database_connection():
        logger.warning("⚠️  verify_database_connection() no disponible")
        pass

# Flag para verificar si estamos en Cloud Functions
# Cloud Functions Gen2 establece estas variables de entorno
IS_CLOUD_FUNCTION = (
    os.getenv("FUNCTION_NAME") is not None or 
    os.getenv("FUNCTION_TARGET") is not None or
    os.getenv("K_SERVICE") is None  # Cloud Run tiene K_SERVICE, Cloud Functions no
)

# Crear aplicación FastAPI
app = FastAPI(
    title="API de Documentos",
    description="API para procesamiento de documentos con IA",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware para verificar DB de forma lazy en Cloud Functions
@app.middleware("http")
async def verify_db_middleware(request: Request, call_next):
    """Middleware que verifica la conexión a DB en la primera solicitud (para Cloud Functions)"""
    if IS_CLOUD_FUNCTION:
        # En Cloud Functions, verificar DB en la primera request
        if not hasattr(app.state, "db_verified"):
            try:
                verify_database_connection()
                app.state.db_verified = True
                logger.info("Conexión a base de datos verificada correctamente (lazy)")
            except Exception as e:
                logger.error(f"Error al verificar base de datos: {e}")
                # No lanzar error aquí para permitir que otros endpoints funcionen
    return await call_next(request)


# Registrar rutas (solo las que se importaron correctamente)
if health_router:
    try:
        app.include_router(health_router)
        logger.info("✅ health_router registrado")
    except Exception as e:
        logger.error(f"Error registrando health_router: {e}", exc_info=True)

if document_router:
    try:
        app.include_router(document_router)
        logger.info("✅ document_router registrado")
    except Exception as e:
        logger.error(f"Error registrando document_router: {e}", exc_info=True)

if document_type_router:
    try:
        app.include_router(document_type_router)
        logger.info("✅ document_type_router registrado")
    except Exception as e:
        logger.error(f"Error registrando document_type_router: {e}", exc_info=True)

if etiqueta_walmart_router:
    try:
        app.include_router(etiqueta_walmart_router)
        logger.info("✅ etiqueta_walmart_router registrado")
    except Exception as e:
        logger.error(f"Error registrando etiqueta_walmart_router: {e}", exc_info=True)

if etiqueta_enviame_router:
    try:
        app.include_router(etiqueta_enviame_router)
        logger.info("✅ etiqueta_enviame_router registrado")
    except Exception as e:
        logger.error(f"Error registrando etiqueta_enviame_router: {e}", exc_info=True)

if certificado_f30_router:
    try:
        app.include_router(certificado_f30_router)
        logger.info("✅ certificado_f30_router registrado")
    except Exception as e:
        logger.error(f"Error registrando certificado_f30_router: {e}", exc_info=True)
else:
    logger.error("❌ certificado_f30_router es None - no se pudo importar el router")

# Agregar endpoint de health check simple que siempre funcione
@app.get("/", tags=["health"])
async def root():
    """Endpoint raíz simple"""
    return {
        "status": "ok",
        "message": "API de Documentos",
        "version": "1.0.0"
    }

@app.get("/health", tags=["health"])
async def simple_health():
    """Health check simple que no depende de nada"""
    return {
        "status": "healthy",
        "service": "API de Documentos"
    }

@app.get("/api/v1/routes", tags=["diagnostic"])
async def list_routes():
    """Endpoint de diagnóstico para listar todas las rutas registradas"""
    routes = []
    for route in app.routes:
        if hasattr(route, "path") and hasattr(route, "methods"):
            routes.append({
                "path": route.path,
                "methods": list(route.methods) if route.methods else [],
                "name": getattr(route, "name", "unknown")
            })
    
    routers_status = {
        "certificado_f30_router": certificado_f30_router is not None,
        "etiqueta_walmart_router": etiqueta_walmart_router is not None,
        "etiqueta_enviame_router": etiqueta_enviame_router is not None,
        "document_router": document_router is not None,
        "document_type_router": document_type_router is not None,
        "health_router": health_router is not None
    }
    
    return {
        "total_routes": len(routes),
        "routes": sorted(routes, key=lambda x: x["path"]),
        "routers_imported": routers_status,
        "import_errors": import_errors if import_errors else {}
    }

logger.info("✅ Rutas registradas (algunas pueden estar ausentes si hubo errores de importación)")


@app.on_event("startup")
async def startup_event():
    """Evento de inicio de la aplicación (solo para Cloud Run/desarrollo local)"""
    import asyncio
    
    try:
        logger.info("🚀 Iniciando API de Documentos...")
        logger.info(f"📊 Entorno: {'Cloud Function' if IS_CLOUD_FUNCTION else 'Cloud Run'}")
        
        # Cloud Run siempre proporciona PORT (generalmente 8080)
        # No usar fallback local para producción
        port = os.getenv('PORT')
        if not port:
            logger.warning("⚠️  PORT no configurado, usando 8080 (puerto por defecto de Cloud Run)")
            port = '8080'
        else:
            logger.info(f"🔌 Puerto: {port} (desde variable de entorno PORT)")
        logger.info(f"🌐 Host: 0.0.0.0 (requerido por Cloud Run)")
        
        # Marcar que el servidor está iniciando (no bloqueante)
        logger.info("✅ API de Documentos iniciada correctamente")
        logger.info(f"✅ Servidor listo para recibir solicitudes en puerto {port}")
        
        # Verificar conexión a base de datos de forma asíncrona y no bloqueante
        if not IS_CLOUD_FUNCTION:
            # Ejecutar verificación en background para no bloquear el startup
            async def verify_db_background():
                try:
                    logger.info("🔍 Verificando conexión a base de datos (background)...")
                    # Ejecutar en thread pool para no bloquear el event loop
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, verify_database_connection)
                    logger.info("✅ Conexión a base de datos verificada correctamente")
                except Exception as e:
                    logger.warning(f"⚠️  No se pudo verificar la conexión a base de datos: {e}")
                    logger.warning("⚠️  La API funcionará pero algunas funciones pueden no estar disponibles")
                    logger.warning("⚠️  La conexión se intentará de nuevo en la primera solicitud")
            
            # Iniciar verificación en background sin esperar
            asyncio.create_task(verify_db_background())
    except Exception as e:
        # NO hacer raise aquí - permitir que el servidor inicie incluso si hay errores
        logger.error(f"Error en startup_event: {e}", exc_info=True)
        logger.warning("⚠️  El servidor iniciará pero puede haber funcionalidades limitadas")


# ============================================
# Cloud Functions Gen2 Support con functions-framework[fastapi]
# ============================================
# IMPORTANTE: Para Cloud Functions Gen2, usa --entry-point=app (NO handler)
# functions-framework[fastapi] detectará automáticamente que 'app' es FastAPI
# y manejará todo correctamente.
#
# El handler solo se usa si necesitas un comportamiento específico, pero
# con functions-framework[fastapi] es mejor usar app directamente.


if __name__ == "__main__":
    # Configuración para desarrollo local
    # NOTA: En Cloud Run, este bloque NO se ejecuta porque el Dockerfile usa uvicorn directamente
    port = os.getenv("PORT", "8000")
    logger.info(f"Iniciando servidor local en puerto {port}")
    logger.warning("⚠️  Este modo es solo para desarrollo local. En Cloud Run se usa el Dockerfile.")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(port),
        reload=False,  # Desactivar reload en producción
        log_level="info"
    )
