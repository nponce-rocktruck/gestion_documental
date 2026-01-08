# Configuración de Máquina Virtual para Verificaciones

## Arquitectura

- **Cloud Run**: API principal, llama a la VM para verificaciones
- **VM**: Servicio de verificación que requiere IP de Sudamérica

## Configuración en la VM

### 1. Instalar dependencias
```bash
cd ~/api-documentos
source venv/bin/activate
pip install fastapi uvicorn
```

### 2. Iniciar servicio
```bash
chmod +x vm_services/start_service.sh
./vm_services/start_service.sh
```

O manualmente:
```bash
cd ~/api-documentos
source venv/bin/activate
python vm_services/verification_api.py
```

### 3. Verificar que funciona
```bash
curl http://localhost:8080/health
```

### 4. Abrir puerto en firewall (desde tu PC)
```bash
gcloud compute firewall-rules create allow-vm-verification-api \
    --allow tcp:8080 \
    --source-ranges 0.0.0.0/0 \
    --description "Allow verification API access to VM"
```

## Configuración en Cloud Run

### Variable de entorno
Agregar en `env.cloud-functions.yaml`:
```yaml
VM_VERIFICATION_URL: "http://34.176.102.209:8080"
VM_REQUEST_TIMEOUT: "120"
```

## Endpoints disponibles en la VM

- `GET /health` - Health check
- `POST /verificar/portal-documental` - Verificación portal documental
- `POST /verificar/persona-natural` - Verificación persona natural

## Mantener servicio corriendo

Para mantener el servicio corriendo en background:
```bash
nohup python vm_services/verification_api.py > vm_service.log 2>&1 &
```

Para ver logs:
```bash
tail -f vm_service.log
```

Para detener:
```bash
pkill -f verification_api.py
```

