"""
Procesadores específicos para cada tipo de documento
"""

from .base_processor import BaseDocumentProcessor
from .etiqueta_walmart_processor import EtiquetaWalmartProcessor
from .etiqueta_enviame_processor import EtiquetaEnviameProcessor
from .certificado_f30_processor import CertificadoF30Processor

__all__ = [
    "BaseDocumentProcessor",
    "EtiquetaWalmartProcessor",
    "EtiquetaEnviameProcessor",
    "CertificadoF30Processor",
]

