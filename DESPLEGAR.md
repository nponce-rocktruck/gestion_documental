# 🚀 Guía Rápida de Despliegue

## Desde CMD (estás en `C:\Users\pc>`)

### Paso 1: Navegar al proyecto

```cmd
cd "Documents\GitHub\API Documentos"
```

### Paso 2: Verificar que tienes gcloud configurado

```cmd
gcloud --version
gcloud config get-value project
```

Si no tienes gcloud configurado:
```cmd
gcloud init
gcloud auth login
```

### Paso 3: Habilitar APIs necesarias (solo la primera vez)

```cmd
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable vision.googleapis.com
```

### Paso 4: Verificar archivo de variables de entorno

Asegúrate de que el archivo `env.cloud-functions.yaml` existe y tiene tus credenciales correctas.

### Paso 5: Desplegar

**Opción A: Usar el script PowerShell (Recomendado)**

```powershell
.\tools\deploy_cloud_run.ps1
```

**Opción B: Comando directo desde CMD**

```cmd
cd "Documents\GitHub\API Documentos"
gcloud run deploy gestiondocumental --source . --platform managed --region us-central1 --allow-unauthenticated --set-env-vars-from-file env.cloud-functions.yaml --memory=2Gi --cpu=2 --timeout=300 --max-instances=10 --min-instances=0 --port=8080
```

**Nota:** Si el comando `--set-env-vars-from-file` no funciona, usa el script PowerShell que lee el YAML correctamente.

### Paso 6: Obtener la URL

```cmd
gcloud run services describe gestiondocumental --region us-central1 --format="value(status.url)"
```

## ✅ Verificar que funciona

```cmd
curl https://TU_URL/health
```

O abre en el navegador: `https://TU_URL/docs`

## 📝 Endpoints Disponibles

- `POST /api/v1/etiqueta_walmart` - Procesar etiqueta Walmart
- `POST /api/v1/etiqueta_enviame` - Procesar etiqueta ENVIAME  
- `POST /api/v1/certificado_f30` - Procesar certificado F30
- `GET /api/v1/documents/{id}/status` - Consultar estado
- `GET /api/v1/documents/{id}/result` - Obtener resultado
- `GET /health` - Health check
- `GET /docs` - Documentación Swagger

## 🔍 Ver Logs

```cmd
gcloud run services logs tail gestiondocumental --region us-central1
```

## 🔄 Actualizar Despliegue

Si haces cambios, simplemente vuelve a ejecutar el paso 5.

