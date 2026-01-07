# =============================================================================
# Script de Despliegue para Cloud Run - API de Documentos
# =============================================================================
# Este script despliega tu API en Google Cloud Run de forma automática
# Usa: .\deploy_cloud_run.ps1

param(
    [string]$ServiceName = "gestiondocumental",
    [string]$Region = "us-central1",
    [string]$EnvFile = "env.cloud-functions.yaml"
)

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "🚀 Despliegue en Cloud Run" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Servicio: $ServiceName" -ForegroundColor Yellow
Write-Host "Región: $Region" -ForegroundColor Yellow
Write-Host "Archivo de variables: $EnvFile" -ForegroundColor Yellow
Write-Host ""

# Verificar que el archivo existe
if (-not (Test-Path $EnvFile)) {
    Write-Host "❌ Error: No se encontró el archivo $EnvFile" -ForegroundColor Red
    Write-Host "💡 Crea el archivo env.cloud-functions.yaml con tus variables" -ForegroundColor Yellow
    exit 1
}

# Leer variables de entorno desde YAML
Write-Host "📋 Leyendo variables de entorno..." -ForegroundColor Cyan

$envVars = @()
$lines = Get-Content $EnvFile
$currentKey = $null
$currentValue = ""
$inMultiLine = $false

foreach ($line in $lines) {
    $trimmedLine = $line.Trim()
    
    # Ignorar comentarios y líneas vacías
    if ($trimmedLine.StartsWith('#') -or [string]::IsNullOrWhiteSpace($trimmedLine)) {
        continue
    }
    
    # Buscar patrones: KEY: "value"
    if ($trimmedLine -match '^([A-Z_][A-Z0-9_]*):\s*"(.+)"\s*$') {
        $key = $matches[1]
        $value = $matches[2]
        # Escapar comillas dobles en el valor para gcloud
        $value = $value -replace '"', '\"'
        $envVars += "$key=$value"
        Write-Host "  ✓ $key" -ForegroundColor Gray
    }
    elseif ($trimmedLine -match '^([A-Z_][A-Z0-9_]*):\s*(.+?)\s*$') {
        $key = $matches[1]
        $value = $matches[2]
        
        # Si el valor contiene { o es muy largo, puede ser JSON
        if ($value -match '^\{"' -or $value.Length -gt 500) {
            $currentKey = $key
            $currentValue = $value
            $inMultiLine = $true
        } else {
            $value = $value -replace '"', '\"'
            $envVars += "$key=$value"
            Write-Host "  ✓ $key" -ForegroundColor Gray
        }
    }
    elseif ($inMultiLine -and $null -ne $currentKey) {
        # Continuación de valor multi-línea
        $currentValue += $line
        if ($trimmedLine.EndsWith('"')) {
            $finalValue = $currentValue -replace '"', '\"' -replace '\n', '' -replace '\r', ''
            $envVars += "$currentKey=$finalValue"
            Write-Host "  ✓ $currentKey (multi-línea)" -ForegroundColor Gray
            $currentKey = $null
            $currentValue = ""
            $inMultiLine = $false
        }
    }
}

# Si quedó algo pendiente
if ($null -ne $currentKey -and $currentValue) {
    $finalValue = $currentValue -replace '"', '\"' -replace '\n', '' -replace '\r', ''
    $envVars += "$currentKey=$finalValue"
    Write-Host "  ✓ $currentKey" -ForegroundColor Gray
}

# Convertir array a string separado por comas
$envVarsString = $envVars -join ','

if ([string]::IsNullOrEmpty($envVarsString)) {
    Write-Host "⚠️  No se encontraron variables de entorno en $EnvFile" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Variables encontradas: $($envVars.Count)" -ForegroundColor Green
Write-Host ""

# Comando de despliegue en Cloud Run
Write-Host "🔨 Iniciando despliegue en Cloud Run..." -ForegroundColor Cyan
Write-Host "⏳ Esto puede tardar 3-5 minutos..." -ForegroundColor Yellow
Write-Host ""

gcloud run deploy $ServiceName `
    --source . `
    --platform managed `
    --region=$Region `
    --allow-unauthenticated `
    --set-env-vars $envVarsString `
    --memory=2Gi `
    --cpu=2 `
    --timeout=300 `
    --max-instances=10 `
    --min-instances=0 `
    --port=8080 `
    --clear-base-image

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "✅ ¡Despliegue exitoso!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    
    # Obtener la URL del servicio
    Write-Host "🔗 Obteniendo URL del servicio..." -ForegroundColor Cyan
    $url = gcloud run services describe $ServiceName --region=$Region --format='value(status.url)' 2>$null
    
    if ($url) {
        Write-Host ""
        Write-Host "📍 URL de tu API:" -ForegroundColor Green
        Write-Host "   $url" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "📝 Endpoints disponibles:" -ForegroundColor Cyan
        Write-Host "   POST   $url/api/v1/etiqueta_walmart" -ForegroundColor Gray
        Write-Host "   POST   $url/api/v1/etiqueta_enviame" -ForegroundColor Gray
        Write-Host "   POST   $url/api/v1/certificado_f30" -ForegroundColor Gray
        Write-Host "   GET    $url/api/v1/documents/{id}/status" -ForegroundColor Gray
        Write-Host "   GET    $url/api/v1/documents/{id}/result" -ForegroundColor Gray
        Write-Host "   GET    $url/health" -ForegroundColor Gray
        Write-Host "   GET    $url/docs" -ForegroundColor Gray
        Write-Host ""
        Write-Host "💾 Guarda esta URL para consumir la API" -ForegroundColor Yellow
    } else {
        Write-Host "   gcloud run services describe $ServiceName --region=$Region --format='value(status.url)'" -ForegroundColor Gray
    }
} else {
    Write-Host ""
    Write-Host "❌ Error en el despliegue. Revisa los mensajes anteriores." -ForegroundColor Red
    Write-Host "💡 Verifica los logs en: https://console.cloud.google.com/run" -ForegroundColor Yellow
}

