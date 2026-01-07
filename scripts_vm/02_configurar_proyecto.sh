#!/bin/bash
# Script para configurar el proyecto en la VM

PROJECT_DIR="$HOME/api-documentos"

echo "=== Creando directorio del proyecto ==="
mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

echo "=== Creando entorno virtual ==="
python3.11 -m venv venv
source venv/bin/activate

echo "=== Instalando pip y dependencias ==="
pip install --upgrade pip
pip install -r requirements.txt

echo "=== Instalando navegadores de Playwright ==="
playwright install chromium
playwright install-deps chromium

echo "=== Configuración completada ==="
echo "Para activar el entorno virtual: source $PROJECT_DIR/venv/bin/activate"

