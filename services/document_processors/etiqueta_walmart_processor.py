"""
Procesador específico para Etiqueta de Envío Walmart
"""

from .base_processor import BaseDocumentProcessor


class EtiquetaWalmartProcessor(BaseDocumentProcessor):
    """Procesador para Etiqueta de Envío Walmart"""
    
    def __init__(self):
        super().__init__(
            document_type_name="Etiqueta de Envío Walmart",
            requires_authenticity=False  # Las etiquetas no requieren autenticidad
        )

