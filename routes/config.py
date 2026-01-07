"""
Configuración de rutas para la API de Documentos
"""

# Configuración de rutas
ROUTE_PREFIXES = {
    "documents": "/api/v1",
    "document_types": "/api/v1", 
    "health": ""
}

# Tags para documentación
ROUTE_TAGS = {
    "documents": ["documents"],
    "document_types": ["document-types"],
    "health": ["health"]
}

# Configuración de respuestas
DEFAULT_RESPONSES = {
    400: {"description": "Solicitud inválida"},
    404: {"description": "Recurso no encontrado"},
    409: {"description": "Conflicto - recurso ya existe"},
    422: {"description": "Error de validación"},
    500: {"description": "Error interno del servidor"}
}
