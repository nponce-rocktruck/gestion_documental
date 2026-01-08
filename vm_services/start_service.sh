#!/bin/bash
# Script para iniciar el servicio de verificación en la VM

cd ~/api-documentos

# Activar entorno virtual
source venv/bin/activate

# Iniciar servicio
python vm_services/verification_api.py

