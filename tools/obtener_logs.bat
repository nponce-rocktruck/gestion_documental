@echo off
REM Script para obtener los logs más recientes de Cloud Run

echo ========================================
echo OBTENER LOGS DE CLOUD RUN
echo ========================================
echo.
echo Opciones:
echo   1. Ver todos los logs recientes
echo   2. Ver solo errores
echo   3. Ver logs de rechazos del portal
echo   4. Ver logs de Walmart
echo   5. Usar script Python (más opciones)
echo.
set /p opcion="Selecciona una opción (1-5): "

if "%opcion%"=="1" (
    echo.
    echo Obteniendo logs recientes...
    gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=gestiondocumental AND resource.labels.location=us-central1" --limit 50 --format="value(timestamp,severity,textPayload)" --freshness=1h
) else if "%opcion%"=="2" (
    echo.
    echo Obteniendo solo errores...
    gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=gestiondocumental AND resource.labels.location=us-central1 AND severity>=ERROR" --limit 50 --format="value(timestamp,severity,textPayload)" --freshness=1h
) else if "%opcion%"=="3" (
    echo.
    echo Obteniendo logs de rechazos del portal...
    gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=gestiondocumental AND resource.labels.location=us-central1 AND (textPayload=~'portal_message' OR textPayload=~'rechazo' OR textPayload=~'no válido' OR textPayload=~'no valido')" --limit 50 --format="value(timestamp,severity,textPayload)" --freshness=1h
) else if "%opcion%"=="4" (
    echo.
    echo Obteniendo logs de Walmart...
    gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=gestiondocumental AND resource.labels.location=us-central1 AND textPayload=~'walmart'" --limit 50 --format="value(timestamp,severity,textPayload)" --freshness=1h
) else if "%opcion%"=="5" (
    echo.
    echo Ejecutando script Python...
    python tools\obtener_logs.py --errores --limit 50
) else (
    echo Opción inválida. Debe ser un número del 1 al 5.
)

echo.
echo ========================================
echo COMANDOS ÚTILES:
echo ========================================
echo Ver logs en tiempo real:
echo   gcloud logging tail "resource.type=cloud_run_revision AND resource.labels.service_name=gestiondocumental"
echo.
echo Ver solo errores:
echo   gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=gestiondocumental AND severity>=ERROR" --limit 100
echo.
echo Ver logs de las últimas 2 horas:
echo   gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=gestiondocumental" --freshness=2h --limit 100
echo.
pause

