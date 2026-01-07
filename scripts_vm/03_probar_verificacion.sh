#!/bin/bash
# Script para probar la verificación del portal

PROJECT_DIR="$HOME/api-documentos"
cd $PROJECT_DIR

# Activar entorno virtual
source venv/bin/activate

# Verificar IP
echo "=== IP de la VM ==="
curl -s ifconfig.me
echo ""

# Ejecutar prueba
echo "=== Ejecutando prueba de verificación ==="
if [ -z "$1" ]; then
    echo "Uso: $0 'XXXX XXXX XXXX'"
    echo "Ejemplo: $0 '1234 5678 9012'"
    exit 1
fi

python test_portal_verification.py "$1"

