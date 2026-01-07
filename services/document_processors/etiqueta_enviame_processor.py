"""
Procesador específico para Etiqueta de Envío ENVIAME
"""

from .base_processor import BaseDocumentProcessor


class EtiquetaEnviameProcessor(BaseDocumentProcessor):
    """Procesador para Etiqueta de Envío ENVIAME"""
    
    def __init__(self):
        super().__init__(
            document_type_name="Etiqueta de Envío ENVIAME",
            requires_authenticity=False  # Las etiquetas no requieren autenticidad
        )

