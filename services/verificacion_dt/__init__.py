"""
Módulo de verificación de códigos en el portal oficial de la Dirección del Trabajo
https://midt.dirtrab.cl/verificadorDocumental
"""

from .portal_verification_service import PortalVerificationService
from .persona_natural_verification_service import PersonaNaturalVerificationService

__all__ = ["PortalVerificationService", "PersonaNaturalVerificationService"]

