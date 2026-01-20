# Configuración de API de Verificación en VM

## Resumen

Se ha implementado una API de verificación en la VM que usa `undetected_chromedriver` + `2captcha` + Oxylabs (como en `project_dt`). Esta API permite verificar códigos y descargar PDFs desde el portal de la DT sin bloqueos.

## Archivos Creados

1. **`vm_services/verification_api.py`**: API FastAPI que expone endpoints de verificación
2. **`services/verificacion_dt/vm_verification_client.py`**: Cliente HTTP para llamar a la API desde Cloud Run
3. **`requirements_vm.txt`**: Dependencias necesarias en la VM

## Configuración en la VM

### 1. Instalar Dependencias

```bash
# En la VM
cd ~/api-documentos
source venv/bin/activate

# Instalar dependencias de la VM
pip install -r requirements_vm.txt
```

### 2. Variables de Entorno

La API lee las siguientes variables de entorno (opcional, tiene valores por defecto):

```bash
export OXY_USER="conirarra_FyqF8"
export OXY_PASS="Clemente_2011"
export OXY_HOST="unblock.oxylabs.io"
export OXY_PORT="60000"
export API_KEY_2CAPTCHA="e716e4f00d5e2225bcd8ed2a04981fe3"
```

**NOTA**: Los valores por defecto están hardcodeados en el código. Se recomienda usar variables de entorno.

### 3. Ejecutar la API

```bash
cd ~/api-documentos
source venv/bin/activate
python vm_services/verification_api.py
```

La API se ejecutará en `http://0.0.0.0:8080`

### 4. Verificar que funciona

```bash
# Health check
curl http://localhost:8080/health

# Probar endpoint
curl -X POST http://localhost:8080/verificar/portal-documental \
  -H "Content-Type: application/json" \
  -d '{"codigo": "ZRQWWEEJKOWQ"}'
```

## Configuración en Cloud Run

### Variables de Entorno

En `env.cloud-functions.yaml`, agregar:

```yaml
VM_VERIFICATION_URL: "http://34.176.102.209:8080"
```

Reemplazar con la IP de tu VM si es diferente.

### Firewall

Asegurarse de que el firewall permita conexiones al puerto 8080:

```bash
gcloud compute firewall-rules create allow-vm-verification-api \
    --allow tcp:8080 \
    --source-ranges 0.0.0.0/0 \
    --description "Allow verification API access to VM"
```

## Endpoints Disponibles

### POST `/verificar/portal-documental`

Verifica código en portal documental y descarga PDF.

**Request:**
```json
{
  "codigo": "ZRQW WEEJ KOWQ"
}
```

**Response:**
```json
{
  "success": true,
  "valid": true,
  "message": "Código válido - PDF obtenido",
  "pdf_base64": "base64_string...",
  "error": null
}
```

### POST `/verificar/persona-natural`

**NOTA**: Pendiente de implementación completa.

Verifica y descarga certificado F30 para persona natural.

**Request:**
```json
{
  "folio_oficina": "XXX",
  "folio_anio": "YYYY",
  "folio_numero": "NNNNN",
  "codigo_verificacion": "XXXXX"
}
```

## Flujo de Trabajo

1. **Cloud Run** recibe request de procesamiento F30
2. **certificado_f30_processor.py** llama a `VMVerificationClient`
3. **VMVerificationClient** hace HTTP POST a la API en la VM
4. **VM API** ejecuta Selenium + 2captcha + Oxylabs
5. **VM API** devuelve PDF en base64
6. **VMVerificationClient** guarda PDF como archivo local
7. **certificado_f30_processor.py** continúa con el flujo normal:
   - Sube PDF a GCS
   - Extrae datos con OCR
   - Compara datos
   - Guarda en BD

## Notas Importantes

1. **La función `verificar_persona_natural_sync` está pendiente de implementación completa**. Por ahora solo funciona `portal-documental`.

2. **El código usa valores hardcodeados** para Oxylabs y 2captcha. Se recomienda mover a variables de entorno.

3. **Chrome debe estar instalado** en la VM. Se asume que ya está instalado.

4. **La API usa ThreadPoolExecutor** para ejecutar Selenium (bloqueante) sin bloquear FastAPI (asíncrono).

5. **El PDF se devuelve en base64** en la respuesta JSON. El cliente lo guarda como archivo temporal.

## Troubleshooting

### La API no inicia
- Verificar que Chrome esté instalado: `google-chrome --version`
- Verificar dependencias: `pip list | grep selenium`

### Error de conexión desde Cloud Run
- Verificar firewall: `gcloud compute firewall-rules list`
- Verificar IP de la VM: `curl ifconfig.me` (desde la VM)
- Verificar que la API esté corriendo: `curl http://VM_IP:8080/health`

### Error en verificación
- Revisar logs de la VM
- Verificar credenciales de Oxylabs
- Verificar API key de 2captcha
- Revisar que el código de verificación sea correcto

