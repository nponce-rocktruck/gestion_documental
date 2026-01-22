#!/bin/bash
# Script para instalar el servicio systemd de la API de verificación

set -e

echo "=========================================="
echo "Instalación del servicio VM Verification API"
echo "=========================================="

# Verificar que estamos en el directorio correcto
if [ ! -f "vm_services/verification_api.py" ]; then
    echo "Error: No se encuentra vm_services/verification_api.py"
    echo "Asegúrate de estar en el directorio del proyecto (api-documentos)"
    exit 1
fi

# Verificar que existe el entorno virtual
if [ ! -d "venv" ]; then
    echo "Error: No se encuentra el entorno virtual (venv)"
    echo "Ejecuta primero: python3 -m venv venv && source venv/bin/activate && pip install -r requirements_vm.txt"
    exit 1
fi

# Copiar archivo de servicio
echo "Copiando archivo de servicio systemd..."
sudo cp scripts_vm/vm-verification-api.service /etc/systemd/system/

# Recargar systemd
echo "Recargando systemd..."
sudo systemctl daemon-reload

# Habilitar servicio para que inicie automáticamente
echo "Habilitando servicio para inicio automático..."
sudo systemctl enable vm-verification-api.service

# Iniciar servicio
echo "Iniciando servicio..."
sudo systemctl start vm-verification-api.service

# Esperar un momento
sleep 2

# Verificar estado
echo ""
echo "Estado del servicio:"
sudo systemctl status vm-verification-api.service --no-pager

echo ""
echo "=========================================="
echo "Instalación completada"
echo "=========================================="
echo ""
echo "Comandos útiles:"
echo "  Ver estado:     sudo systemctl status vm-verification-api"
echo "  Ver logs:        sudo journalctl -u vm-verification-api -f"
echo "  Reiniciar:       sudo systemctl restart vm-verification-api"
echo "  Detener:         sudo systemctl stop vm-verification-api"
echo "  Iniciar:         sudo systemctl start vm-verification-api"
echo ""

