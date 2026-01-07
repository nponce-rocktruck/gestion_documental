"""
Script de prueba independiente para verificar códigos en el portal de la Dirección del Trabajo
y descargar archivos de certificados.

Uso:
    python test_portal_verification.py
    python test_portal_verification.py "1234 5678 9012"
"""

import sys
import logging
from pathlib import Path

# Configurar logging para ver el progreso
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

# Agregar el directorio raíz al path para importar el servicio
sys.path.insert(0, str(Path(__file__).parent))

from services.verificacion_dt.portal_verification_service import PortalVerificationService


def main():
    """Función principal para probar la verificación del portal"""
    
    print("=" * 70)
    print("PRUEBA DE VERIFICACIÓN DE CÓDIGO - PORTAL DIRECCIÓN DEL TRABAJO")
    print("=" * 70)
    print()
    
    # Obtener código de verificación
    if len(sys.argv) > 1:
        codigo = sys.argv[1]
        print(f"Código proporcionado: {codigo}")
    else:
        # Solicitar código al usuario
        codigo = input("Ingrese el código de verificación (formato: XXXX XXXX XXXX): ").strip()
        if not codigo:
            print("❌ Error: Debe proporcionar un código de verificación")
            print("\nUso:")
            print("  python test_portal_verification.py")
            print("  python test_portal_verification.py \"1234 5678 9012\"")
            return
    
    print(f"\n🔍 Verificando código: {codigo}")
    print("-" * 70)
    
    # Crear directorio de descargas si no existe
    download_dir = Path(__file__).parent / "downloads"
    download_dir.mkdir(exist_ok=True)
    print(f"📁 Directorio de descargas: {download_dir}")
    print()
    
    # Inicializar servicio
    # En VM sin display, usar headless=True automáticamente
    import os
    has_display = os.getenv("DISPLAY") is not None
    headless_mode = not has_display  # True si no hay display (VM)
    
    service = PortalVerificationService(
        headless=headless_mode,
        download_dir=str(download_dir)
    )
    
    try:
        # Ejecutar verificación
        print("⏳ Iniciando verificación...")
        print()
        
        result = service.verify_code(codigo, timeout=90)
        
        # Mostrar resultados
        print()
        print("=" * 70)
        print("RESULTADOS DE LA VERIFICACIÓN")
        print("=" * 70)
        print()
        
        if result["success"]:
            print("✅ Verificación completada exitosamente")
            print()
            
            if result["valid"]:
                print("✅ CÓDIGO VÁLIDO")
                print()
                
                if result.get("downloaded_file"):
                    file_path = Path(result["downloaded_file"])
                    file_size = file_path.stat().st_size if file_path.exists() else 0
                    print(f"📄 Archivo descargado:")
                    print(f"   Ruta: {result['downloaded_file']}")
                    print(f"   Tamaño: {file_size:,} bytes")
                    print(f"   Existe: {'Sí' if file_path.exists() else 'No'}")
                else:
                    print("⚠️  No se detectó descarga de archivo")
                
                if result.get("portal_message"):
                    print(f"💬 Mensaje del portal: {result['portal_message']}")
            else:
                print("❌ CÓDIGO INVÁLIDO")
                print()
                
                if result.get("error_message"):
                    print(f"💬 Mensaje de error: {result['error_message']}")
                elif result.get("portal_message"):
                    print(f"💬 Mensaje del portal: {result['portal_message']}")
        else:
            print("❌ Error durante la verificación")
            print()
            
            if result.get("error"):
                print(f"🔴 Error: {result['error']}")
        
        print()
        print("-" * 70)
        print("Detalles completos del resultado:")
        print("-" * 70)
        for key, value in result.items():
            print(f"  {key}: {value}")
        
        print()
        print("=" * 70)
        
        # Retornar código de salida apropiado
        if result["success"] and result["valid"]:
            sys.exit(0)
        else:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Verificación cancelada por el usuario")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Error inesperado: {e}")
        logger.exception("Error durante la prueba")
        sys.exit(1)


if __name__ == "__main__":
    main()

