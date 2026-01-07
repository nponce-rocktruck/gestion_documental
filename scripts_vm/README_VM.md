# Configuración de VM para Pruebas

## Pasos para configurar la VM

### 1. Conectarse a la VM

```bash
# Desde tu máquina local, conectarte por SSH
gcloud compute ssh mv-2-southamerica --zone=southamerica-west1-b
```

### 2. Subir archivos del proyecto

Desde tu máquina local (en otra terminal):

```bash
# Ir al directorio del proyecto
cd "C:\Users\pc\Documents\GitHub\API Documentos"

# Subir archivos a la VM
gcloud compute scp --recurse . mv-2-southamerica:~/api-documentos --zone=southamerica-west1-b
```

O clonar desde Git si tienes el repositorio:

```bash
# En la VM
cd ~
git clone <tu-repositorio> api-documentos
cd api-documentos
```

### 3. Ejecutar scripts de configuración

En la VM:

```bash
# Dar permisos de ejecución
chmod +x scripts_vm/*.sh

# Ejecutar instalación de dependencias
./scripts_vm/01_instalar_dependencias.sh

# Configurar proyecto
./scripts_vm/02_configurar_proyecto.sh
```

### 4. Probar verificación

```bash
# Activar entorno virtual
source ~/api-documentos/venv/bin/activate

# Ejecutar prueba
python test_portal_verification.py "XXXX XXXX XXXX"
```

## Verificar IP de la VM

```bash
curl ifconfig.me
# Debería mostrar: 34.176.102.209
```

## Si necesitas instalar manualmente

```bash
# Python y pip
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3-pip

# Crear entorno virtual
python3.11 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt

# Instalar Playwright
playwright install chromium
playwright install-deps chromium
```

## Verificar que funciona

```bash
# Probar Playwright
python -c "from playwright.sync_api import sync_playwright; print('Playwright OK')"

# Probar acceso a internet
curl https://midt.dirtrab.cl/verificadorDocumental
```

