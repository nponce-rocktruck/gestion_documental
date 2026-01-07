@echo off
REM Script de despliegue para CMD que lee variables desde env.cloud-functions.yaml
REM Ejecuta: DESPLEGAR.bat

setlocal enabledelayedexpansion

echo.
echo ========================================
echo Despliegue en Cloud Run
echo ========================================
echo.

set "ENV_FILE=env.cloud-functions.yaml"
set "SERVICE_NAME=gestiondocumental"
set "REGION=us-central1"

REM Verificar que el archivo existe
if not exist "%ENV_FILE%" (
    echo ERROR: No se encontro el archivo %ENV_FILE%
    echo Crea el archivo env.cloud-functions.yaml con tus variables
    pause
    exit /b 1
)

echo Leyendo variables desde %ENV_FILE%...
echo.

REM Variables a buscar
set "MONGODB_URL="
set "MONGODB_DATABASE="
set "AI_API_KEY="
set "AI_BASE_URL="
set "AI_MODEL="
set "OCR_PROVIDER="
set "GCP_PROJECT_ID="
set "LOG_LEVEL="

REM Usar script PowerShell separado para parsear YAML
if exist "parse_yaml.ps1" (
    for /f "tokens=1* delims==" %%a in ('powershell -ExecutionPolicy Bypass -File parse_yaml.ps1 "%ENV_FILE%" 2^>nul') do (
        set "key=%%a"
        set "value=%%b"
        
        REM Asignar valores según la clave
        if /i "!key!"=="MONGODB_URL" set "MONGODB_URL=!value!"
        if /i "!key!"=="MONGODB_DATABASE" set "MONGODB_DATABASE=!value!"
        if /i "!key!"=="AI_API_KEY" set "AI_API_KEY=!value!"
        if /i "!key!"=="AI_BASE_URL" set "AI_BASE_URL=!value!"
        if /i "!key!"=="AI_MODEL" set "AI_MODEL=!value!"
        if /i "!key!"=="OCR_PROVIDER" set "OCR_PROVIDER=!value!"
        if /i "!key!"=="GCP_PROJECT_ID" set "GCP_PROJECT_ID=!value!"
        if /i "!key!"=="LOG_LEVEL" set "LOG_LEVEL=!value!"
    )
) else (
    echo ERROR: No se encontro parse_yaml.ps1
    echo Creando script PowerShell...
    
    REM Crear script PowerShell si no existe
    (
        echo # Script PowerShell para parsear YAML y extraer variables
        echo $envFile = $args[0]
        echo.
        echo if ^(-not ^(Test-Path $envFile^)^) ^{
        echo     Write-Error "Archivo no encontrado: $envFile"
        echo     exit 1
        echo }
        echo.
        echo $content = Get-Content $envFile -Raw
        echo $lines = $content -split "`n"
        echo.
        echo foreach ^($line in $lines^) ^{
        echo     $trimmed = $line.Trim^(^)
        echo     if ^($trimmed -and -not $trimmed.StartsWith^('#'^)^) ^{
        echo         if ^($trimmed -match '^([A-Z_]+^):\s*"(.+^)"$'^) ^{
        echo             $key = $matches[1]
        echo             $value = $matches[2]
        echo             Write-Output "$key=$value"
        echo         }
        echo     }
        echo }
    ) > parse_yaml.ps1
    
    REM Intentar de nuevo
    for /f "tokens=1* delims==" %%a in ('powershell -ExecutionPolicy Bypass -File parse_yaml.ps1 "%ENV_FILE%" 2^>nul') do (
        set "key=%%a"
        set "value=%%b"
        
        REM Asignar valores según la clave
        if /i "!key!"=="MONGODB_URL" set "MONGODB_URL=!value!"
        if /i "!key!"=="MONGODB_DATABASE" set "MONGODB_DATABASE=!value!"
        if /i "!key!"=="AI_API_KEY" set "AI_API_KEY=!value!"
        if /i "!key!"=="AI_BASE_URL" set "AI_BASE_URL=!value!"
        if /i "!key!"=="AI_MODEL" set "AI_MODEL=!value!"
        if /i "!key!"=="OCR_PROVIDER" set "OCR_PROVIDER=!value!"
        if /i "!key!"=="GCP_PROJECT_ID" set "GCP_PROJECT_ID=!value!"
        if /i "!key!"=="LOG_LEVEL" set "LOG_LEVEL=!value!"
    )
)

REM Verificar que se encontraron las variables esenciales
if "!MONGODB_URL!"=="" (
    echo ERROR: No se encontro MONGODB_URL en el archivo
    echo.
    echo Por favor verifica que el archivo %ENV_FILE% tenga el formato correcto:
    echo MONGODB_URL: "valor"
    pause
    exit /b 1
)

if "!AI_API_KEY!"=="" (
    echo ERROR: No se encontro AI_API_KEY en el archivo
    echo.
    echo Por favor verifica que el archivo %ENV_FILE% tenga el formato correcto:
    echo AI_API_KEY: "valor"
    pause
    exit /b 1
)

REM Usar valores por defecto si no se especificaron
if "!MONGODB_DATABASE!"=="" set "MONGODB_DATABASE=Rocktruck"
if "!AI_BASE_URL!"=="" set "AI_BASE_URL=https://api.deepseek.com/v1"
if "!AI_MODEL!"=="" set "AI_MODEL=deepseek-chat"
if "!OCR_PROVIDER!"=="" set "OCR_PROVIDER=gcp"
if "!GCP_PROJECT_ID!"=="" set "GCP_PROJECT_ID=gestiondocumental-473815"
if "!LOG_LEVEL!"=="" set "LOG_LEVEL=INFO"

echo Variables encontradas:
echo   MONGODB_URL: !MONGODB_URL!
echo   MONGODB_DATABASE: !MONGODB_DATABASE!
if not "!AI_API_KEY!"=="" (
    set "AI_KEY_DISPLAY=!AI_API_KEY:~0,20!..."
    echo   AI_API_KEY: !AI_KEY_DISPLAY! (oculto por seguridad)
) else (
    echo   AI_API_KEY: NO ENCONTRADO
)
echo   AI_BASE_URL: !AI_BASE_URL!
echo   AI_MODEL: !AI_MODEL!
echo   OCR_PROVIDER: !OCR_PROVIDER!
echo   GCP_PROJECT_ID: !GCP_PROJECT_ID!
echo   LOG_LEVEL: !LOG_LEVEL!
echo.

REM Construir el comando con las variables leidas
echo Iniciando despliegue...
echo.

REM Construir el comando de variables de entorno correctamente
REM Para gcloud, los valores deben estar entre comillas si tienen caracteres especiales
REM Usar ^ para escapar comillas dentro de la cadena
set "ENV_VARS=MONGODB_URL=^"!MONGODB_URL!^",MONGODB_DATABASE=^"!MONGODB_DATABASE!^",AI_API_KEY=^"!AI_API_KEY!^",AI_BASE_URL=^"!AI_BASE_URL!^",AI_MODEL=^"!AI_MODEL!^",OCR_PROVIDER=^"!OCR_PROVIDER!^",GCP_PROJECT_ID=^"!GCP_PROJECT_ID!^",LOG_LEVEL=^"!LOG_LEVEL!^""

echo Verificando variables antes del despliegue...
echo   MONGODB_URL (primeros 30 chars): !MONGODB_URL:~0,30!...
echo.

gcloud run deploy %SERVICE_NAME% --source . --platform managed --region %REGION% --allow-unauthenticated --set-env-vars %ENV_VARS% --memory=2Gi --cpu=2 --timeout=300 --max-instances=10 --min-instances=0 --port=8080 --clear-base-image

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo Despliegue exitoso!
    echo ========================================
    echo.
    echo Obteniendo URL del servicio...
    gcloud run services describe %SERVICE_NAME% --region %REGION% --format="value(status.url)"
    echo.
    echo Guarda esta URL para consumir la API
) else (
    echo.
    echo ERROR: Error en el despliegue. Revisa los mensajes anteriores.
)

echo.
pause
