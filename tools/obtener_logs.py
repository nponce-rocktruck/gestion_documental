"""
Script para obtener y filtrar logs de Cloud Run
"""

import subprocess
import sys
import json
from datetime import datetime, timedelta
from typing import List, Optional

SERVICE_NAME = "gestiondocumental"
REGION = "us-central1"

def obtener_logs(limit: int = 100, filtro: Optional[str] = None, minutos_atras: int = 60) -> List[str]:
    """
    Obtiene logs de Cloud Run
    
    Args:
        limit: Número máximo de líneas de log a obtener
        filtro: Texto para filtrar los logs (ej: "ERROR", "walmart")
        minutos_atras: Minutos hacia atrás desde ahora para buscar logs
    """
    print(f"🔍 Obteniendo logs de Cloud Run...")
    print(f"   Servicio: {SERVICE_NAME}")
    print(f"   Región: {REGION}")
    print(f"   Límite: {limit} líneas")
    if filtro:
        print(f"   Filtro: '{filtro}'")
    print()
    
    # Calcular tiempo de inicio
    tiempo_inicio = datetime.utcnow() - timedelta(minutes=minutos_atras)
    tiempo_inicio_str = tiempo_inicio.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # Construir comando
    cmd = [
        "gcloud", "logging", "read",
        f"resource.type=cloud_run_revision AND resource.labels.service_name={SERVICE_NAME} AND resource.labels.location={REGION}",
        f"--limit={limit}",
        f"--format=json",
        f"--freshness={minutos_atras}m"
    ]
    
    try:
        print("⏳ Ejecutando comando...")
        resultado = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        # Parsear JSON
        logs = []
        for linea in resultado.stdout.strip().split('\n'):
            if linea.strip():
                try:
                    log_entry = json.loads(linea)
                    logs.append(log_entry)
                except json.JSONDecodeError:
                    continue
        
        print(f"✅ Se obtuvieron {len(logs)} entradas de log\n")
        
        # Procesar y mostrar logs
        if filtro:
            logs_filtrados = filtrar_logs(logs, filtro)
            mostrar_logs(logs_filtrados)
            return logs_filtrados
        else:
            mostrar_logs(logs)
            return logs
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error al ejecutar comando: {e}")
        print(f"   Salida: {e.stdout}")
        print(f"   Error: {e.stderr}")
        return []
    except FileNotFoundError:
        print("❌ Error: No se encontró 'gcloud'. Asegúrate de tener Google Cloud SDK instalado.")
        print("   Instala desde: https://cloud.google.com/sdk/docs/install")
        return []


def filtrar_logs(logs: List[dict], filtro: str) -> List[dict]:
    """Filtra logs que contengan el texto especificado"""
    filtro_lower = filtro.lower()
    logs_filtrados = []
    
    for log in logs:
        texto = log.get("textPayload", "") or log.get("jsonPayload", {}).get("message", "") or ""
        if filtro_lower in texto.lower():
            logs_filtrados.append(log)
    
    return logs_filtrados


def mostrar_logs(logs: List[dict]):
    """Muestra los logs de forma legible"""
    if not logs:
        print("📭 No se encontraron logs")
        return
    
    print("=" * 80)
    print(f"📋 LOGS ({len(logs)} entradas)")
    print("=" * 80)
    print()
    
    for log in logs:
        # Extraer información
        timestamp = log.get("timestamp", "")
        severity = log.get("severity", "INFO")
        text_payload = log.get("textPayload", "")
        json_payload = log.get("jsonPayload", {})
        
        # Formatear timestamp
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                timestamp_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                timestamp_str = timestamp
        else:
            timestamp_str = "N/A"
        
        # Determinar mensaje
        if text_payload:
            mensaje = text_payload
        elif json_payload:
            mensaje = json_payload.get("message", str(json_payload))
        else:
            mensaje = str(log)
        
        # Color según severidad
        if severity == "ERROR":
            icon = "❌"
            color_code = "\033[91m"  # Rojo
        elif severity == "WARNING":
            icon = "⚠️"
            color_code = "\033[93m"  # Amarillo
        elif severity == "INFO":
            icon = "ℹ️"
            color_code = "\033[94m"  # Azul
        else:
            icon = "📝"
            color_code = "\033[0m"   # Normal
        
        reset_code = "\033[0m"
        
        # Mostrar log
        print(f"{color_code}{icon} [{timestamp_str}] [{severity}]{reset_code}")
        print(f"   {mensaje}")
        print()


def obtener_logs_errores(limit: int = 50):
    """Obtiene solo los logs de error"""
    print("🔴 Buscando solo errores...\n")
    return obtener_logs(limit=limit, filtro="ERROR")


def obtener_logs_walmart(limit: int = 50):
    """Obtiene logs relacionados con Walmart"""
    print("🛒 Buscando logs de Walmart...\n")
    return obtener_logs(limit=limit, filtro="walmart")


def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Obtener logs de Cloud Run")
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Número máximo de líneas de log (default: 100)"
    )
    parser.add_argument(
        "--filtro",
        type=str,
        help="Filtrar logs por texto (ej: ERROR, walmart, document_id)"
    )
    parser.add_argument(
        "--errores",
        action="store_true",
        help="Mostrar solo errores"
    )
    parser.add_argument(
        "--walmart",
        action="store_true",
        help="Mostrar solo logs de Walmart"
    )
    parser.add_argument(
        "--minutos",
        type=int,
        default=60,
        help="Minutos hacia atrás para buscar logs (default: 60)"
    )
    
    args = parser.parse_args()
    
    if args.errores:
        obtener_logs_errores(limit=args.limit)
    elif args.walmart:
        obtener_logs_walmart(limit=args.limit)
    else:
        obtener_logs(limit=args.limit, filtro=args.filtro, minutos_atras=args.minutos)


if __name__ == "__main__":
    main()

