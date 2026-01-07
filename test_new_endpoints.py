"""
Script de prueba para los nuevos endpoints específicos por tipo de documento
"""

import requests
import json
import time
import logging
from typing import Dict, Any, Optional

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

#API_BASE_URL = "http://localhost:8000"  
# Cloud Run URL (actualizada después del despliegue)
API_BASE_URL = "https://gestiondocumental-668060986147.us-central1.run.app"
# Cloud Functions URL (si prefieres usar Cloud Functions)
# API_BASE_URL = "https://us-central1-gestiondocumental-473815.cloudfunctions.net/gestiondocumental" 



def test_certificado_f30() -> bool:
    """Prueba el endpoint de Certificado F30 - Razón Social"""
    logger.info("=" * 60)
    logger.info("Probando endpoint: /api/v1/certificado_f30 (RAZÓN SOCIAL)")
    logger.info("=" * 60)
    
    url = f"{API_BASE_URL}/api/v1/certificado_f30"
    payload = {
        "document_id": f"f30-razon-social-test-{int(time.time())}",
        "file_url": "https://storage.googleapis.com/rocktruck-prd/binnacle/-1743791247010_F30_MARZO_2025.pdf-4-4-2025 18:27:27.pdf",
        "origin": "test_system",
        "destination": "test_destination",
        "tipo_f30": "razon_social",
        "user_data": {
            "razon_social_empleador": "SOC COMERCIAL GAS MACUL LIMITADA",
            "rut_empleador": "77301140-0",
            "rut": "77301140-0",
            "name": "SOC COMERCIAL GAS MACUL LIMITADA",
            "business_name": "SOC COMERCIAL GAS MACUL LIMITADA"
        },
        "response_url": None
    }
    
    try:
        # Aumentar timeout a 60 segundos para evitar timeouts
        response = requests.post(url, json=payload, timeout=60)
        logger.info(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"✓ Solicitud aceptada")
            logger.info(f"  Document ID: {result.get('document_id')}")
            logger.info(f"  Status: {result.get('status')}")
            return True
        else:
            logger.error(f"✗ Error: {response.status_code}")
            logger.error(f"  Response: {response.text}")
            return False
    except Exception as e:
        logger.error(f"✗ Error: {e}")
        return False


def test_certificado_f30_persona_natural() -> bool:
    """Prueba el endpoint de Certificado F30 - Persona Natural"""
    logger.info("=" * 60)
    logger.info("Probando endpoint: /api/v1/certificado_f30 (PERSONA NATURAL)")
    logger.info("=" * 60)
    
    url = f"{API_BASE_URL}/api/v1/certificado_f30"
    payload = {
        "document_id": f"f30-persona-natural-test-{int(time.time())}",
        "file_url": "https://storage.googleapis.com/rocktruck-prd/binnacle/-1756780754086_f30 ruth aguayo.pdf-2-9-2025 2:39:14.pdf",
        "origin": "test_system",
        "destination": "test_destination",
        "tipo_f30": "persona_natural",
        "user_data": {
            "rut": "12102703-8",
            "run": "12102703-8",
            "national_id": "12102703-8",
            "name": "RUTH MARINA AGUAYO SAEZ",
            "full_name": "RUTH MARINA AGUAYO SAEZ"
        },
        "response_url": None
    }
    
    try:
        # Aumentar timeout a 60 segundos para evitar timeouts
        response = requests.post(url, json=payload, timeout=60)
        logger.info(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"✓ Solicitud aceptada")
            logger.info(f"  Document ID: {result.get('document_id')}")
            logger.info(f"  Status: {result.get('status')}")
            return True
        else:
            logger.error(f"✗ Error: {response.status_code}")
            logger.error(f"  Response: {response.text}")
            return False
    except Exception as e:
        logger.error(f"✗ Error: {e}")
        return False


def load_documents_from_file(file_path: str) -> list:
    """Carga documentos desde un archivo JSON"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"Archivo {file_path} no encontrado, usando lista por defecto")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Error al parsear JSON: {e}")
        return []


def test_certificado_f30_batch() -> Dict[str, bool]:
    """Prueba el endpoint de Certificado F30 con múltiples documentos (razón social y persona natural)"""
    logger.info("=" * 60)
    logger.info("Probando endpoint: /api/v1/certificado_f30 (MÚLTIPLES DOCUMENTOS)")
    logger.info("=" * 60)
    
    # Verificar que el endpoint esté disponible
    logger.info("Verificando disponibilidad del endpoint...")
    try:
        # Intentar acceder a /docs para ver las rutas disponibles
        docs_url = f"{API_BASE_URL}/docs"
        docs_response = requests.get(docs_url, timeout=10)
        logger.info(f"  /docs status: {docs_response.status_code}")
        if docs_response.status_code == 200:
            logger.info(f"  ✓ Documentación disponible en: {docs_url}")
            logger.info(f"  Revisa la documentación para verificar si /api/v1/certificado_f30 está listado")
        
        # Intentar acceder a /health para verificar que el servidor responde
        health_url = f"{API_BASE_URL}/health"
        health_response = requests.get(health_url, timeout=10)
        logger.info(f"  /health status: {health_response.status_code}")
        if health_response.status_code == 200:
            logger.info(f"  ✓ Servidor respondiendo correctamente")
            logger.info(f"  /health response: {health_response.json()}")
        else:
            logger.warning(f"  ⚠ Servidor no responde correctamente en /health")
        
        # Intentar acceder a /api/v1/certificado_f30 con OPTIONS para ver si existe
        options_url = f"{API_BASE_URL}/api/v1/certificado_f30"
        try:
            options_response = requests.options(options_url, timeout=10)
            logger.info(f"  OPTIONS /api/v1/certificado_f30 status: {options_response.status_code}")
            if options_response.status_code != 404:
                logger.info(f"  ✓ Endpoint existe (status: {options_response.status_code})")
            else:
                logger.error(f"  ✗ Endpoint NO existe (404)")
        except Exception as opt_e:
            logger.warning(f"  Error en OPTIONS: {opt_e}")
        
        # Verificar otros endpoints similares para comparar
        test_endpoints = [
            "/api/v1/etiqueta_walmart",
            "/api/v1/etiqueta_enviame"
        ]
        for endpoint in test_endpoints:
            try:
                test_url = f"{API_BASE_URL}{endpoint}"
                test_response = requests.options(test_url, timeout=5)
                if test_response.status_code != 404:
                    logger.info(f"  ✓ {endpoint} existe (status: {test_response.status_code})")
                else:
                    logger.warning(f"  ⚠ {endpoint} también devuelve 404")
            except:
                pass
        
        # Consultar endpoint de diagnóstico para ver rutas registradas
        try:
            routes_url = f"{API_BASE_URL}/api/v1/routes"
            routes_response = requests.get(routes_url, timeout=10)
            if routes_response.status_code == 200:
                routes_data = routes_response.json()
                logger.info(f"  ✓ Endpoint de diagnóstico disponible")
                logger.info(f"  Total rutas registradas: {routes_data.get('total_routes', 0)}")
                logger.info(f"  Routers importados:")
                routers = routes_data.get('routers_imported', {})
                for router_name, is_imported in routers.items():
                    status = "✓" if is_imported else "✗"
                    logger.info(f"    {status} {router_name}: {is_imported}")
                
                # Mostrar errores de importación si existen
                import_errors = routes_data.get('import_errors', {})
                if import_errors:
                    logger.error(f"  ✗ Errores de importación encontrados:")
                    for router_name, error_msg in import_errors.items():
                        logger.error(f"    - {router_name}: {error_msg}")
                
                # Buscar si certificado_f30 está en las rutas
                f30_routes = [r for r in routes_data.get('routes', []) if 'certificado_f30' in r.get('path', '')]
                if f30_routes:
                    logger.info(f"  ✓ Rutas de certificado_f30 encontradas:")
                    for route in f30_routes:
                        logger.info(f"    - {route.get('path')} {route.get('methods')}")
                else:
                    logger.error(f"  ✗ No se encontraron rutas de certificado_f30 en las rutas registradas")
            else:
                logger.warning(f"  ⚠ Endpoint de diagnóstico no disponible (status: {routes_response.status_code})")
        except Exception as diag_e:
            logger.warning(f"  Error consultando diagnóstico: {diag_e}")
        
    except Exception as e:
        logger.warning(f"  Error verificando disponibilidad: {e}")
    
    logger.info("")
    
    # Lista de documentos a probar con su tipo
    documentos = [
        {
            "file_url": "https://storage.googleapis.com/rocktruck-prd/billing/-1765977710704_F30%20noviembre%202025.pdf-17-12-2025%2013:21:50.pdf",
            "tipo_f30": "persona_natural",
            "rut": "12.102.703-8",
            "name": "RUTH MARINA AGUAYO SAEZ"
        }
    ]
    
    if not documentos:
        logger.error("No hay documentos para probar")
        return {}
    
    url = f"{API_BASE_URL}/api/v1/certificado_f30"
    results = {}
    
    for idx, doc in enumerate(documentos, 1):
        logger.info("")
        logger.info(f"--- Documento {idx}/{len(documentos)} ---")
        logger.info(f"Tipo: {doc.get('tipo_f30', 'razon_social').upper()}")
        logger.info(f"URL: {doc['file_url']}")
        
        # Generar document_id único
        timestamp = int(time.time())
        document_id = f"f30-batch-{idx}-{doc.get('tipo_f30', 'razon_social')}-{timestamp}"
        
        tipo_f30 = doc.get("tipo_f30", "razon_social")
        
        # Preparar user_data según el tipo
        if tipo_f30 == "persona_natural":
            rut_limpio = doc["rut"].replace(".", "").replace("-", "")
            logger.info(f"RUT: {doc['rut']}")
            logger.info(f"Nombre: {doc['name']}")
            user_data = {
                "rut": rut_limpio,
                "run": rut_limpio,
                "national_id": rut_limpio,
                "name": doc["name"],
                "full_name": doc["name"]
            }
            # Agregar periodo_a_validar si está presente
            if "periodo_a_validar" in doc:
                user_data["periodo_a_validar"] = doc["periodo_a_validar"]
                logger.info(f"Período a validar: {doc['periodo_a_validar']}")
        else:  # razon_social
            rut_empleador_limpio = doc["rut_empleador"].replace(".", "").replace("-", "")
            logger.info(f"RUT Empleador: {doc['rut_empleador']}")
            logger.info(f"Razón Social: {doc['razon_social']}")
            user_data = {
                "razon_social_empleador": doc["razon_social"],
                "rut_empleador": rut_empleador_limpio,
                "rut": rut_empleador_limpio,
                "name": doc["razon_social"],
                "business_name": doc["razon_social"]
            }
            # Agregar periodo_a_validar si está presente
            if "periodo_a_validar" in doc:
                user_data["periodo_a_validar"] = doc["periodo_a_validar"]
                logger.info(f"Período a validar: {doc['periodo_a_validar']}")
        
        payload = {
            "document_id": document_id,
            "file_url": doc["file_url"],
            "origin": "test_system",
            "destination": "test_destination",
            "tipo_f30": tipo_f30,
            "user_data": user_data,
            "response_url": None
        }
        
        try:
            # Aumentar timeout a 120 segundos para documentos grandes
            logger.info(f"  Enviando POST a: {url}")
            logger.info(f"  Payload keys: {list(payload.keys())}")
            response = requests.post(url, json=payload, timeout=120)
            logger.info(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✓ Solicitud aceptada")
                logger.info(f"  Document ID: {result.get('document_id')}")
                logger.info(f"  Status: {result.get('status')}")
                results[document_id] = True
            elif response.status_code == 404:
                logger.error(f"✗ Error 404: Endpoint no encontrado")
                logger.error(f"  URL intentada: {url}")
                logger.error(f"  Response: {response.text}")
                logger.error(f"  Headers: {dict(response.headers)}")
                logger.error(f"  Posibles causas:")
                logger.error(f"    1. El router no está registrado en el servidor")
                logger.error(f"    2. La URL base es incorrecta")
                logger.error(f"    3. El endpoint no está desplegado correctamente")
                logger.error(f"  Sugerencia: Verifica los logs del servidor para ver si el router se importó correctamente")
                results[document_id] = False
            else:
                logger.error(f"✗ Error: {response.status_code}")
                logger.error(f"  Response: {response.text}")
                logger.error(f"  Headers: {dict(response.headers)}")
                results[document_id] = False
        except requests.exceptions.Timeout:
            logger.error(f"✗ Timeout: El servidor tardó más de 120 segundos en responder")
            logger.error(f"  El documento puede estar siendo procesado, verifica manualmente el estado")
            results[document_id] = False
        except requests.exceptions.RequestException as e:
            logger.error(f"✗ Error de conexión: {e}")
            results[document_id] = False
        except Exception as e:
            logger.error(f"✗ Error: {e}")
            results[document_id] = False
        
        # Pequeña pausa entre solicitudes
        if idx < len(documentos):
            time.sleep(1)
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("RESUMEN DE PRUEBAS BATCH")
    logger.info("=" * 60)
    for doc_id, success in results.items():
        status = "✓ PASÓ" if success else "✗ FALLÓ"
        logger.info(f"{doc_id}: {status}")
    
    return results


def get_document_result(document_id: str, max_attempts: int = 30) -> Optional[Dict[str, Any]]:
    """Obtiene el resultado del procesamiento esperando a que esté listo"""
    logger.info(f"Esperando resultado para documento {document_id}...")
    
    for attempt in range(max_attempts):
        try:
            # Consultar estado
            status_response = requests.get(
                f"{API_BASE_URL}/api/v1/documents/{document_id}/status",
                timeout=10
            )
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                status = status_data.get("status")
                logger.info(f"  Intento {attempt + 1}/{max_attempts}: Estado = {status}")
                
                if status == "COMPLETED":
                    # Obtener resultado completo
                    result_response = requests.get(
                        f"{API_BASE_URL}/api/v1/documents/{document_id}/result",
                        timeout=10
                    )
                    if result_response.status_code == 200:
                        return result_response.json()
                elif status == "FAILED":
                    logger.error("✗ El procesamiento falló")
                    return None
                else:
                    time.sleep(10)  # Esperar 10 segundos
            else:
                logger.warning(f"  Error consultando estado: {status_response.status_code}")
                time.sleep(5)
                
        except Exception as e:
            logger.warning(f"  Error en intento {attempt + 1}: {e}")
            time.sleep(5)
    
    logger.warning("✗ Timeout esperando resultado")
    return None


def test_with_result_check(endpoint_name: str, test_func) -> bool:
    """Ejecuta una prueba y verifica el resultado"""
    success = test_func()
    
    if success:
        logger.info("\n" + "-" * 60)
        logger.info("Nota: Para ver el resultado completo, consulta el endpoint:")
        logger.info(f"  GET /api/v1/documents/{{document_id}}/result")
        logger.info("-" * 60 + "\n")
    
    return success


def main():
    """Función principal"""
    import sys
    
    # Por defecto ejecutar batch, a menos que se especifique --single
    run_single = "--single" in sys.argv or "-s" in sys.argv
    run_batch = not run_single  # Por defecto ejecutar batch
    
    logger.info("=" * 60)
    logger.info("PRUEBAS DE NUEVOS ENDPOINTS ESPECÍFICOS")
    logger.info("=" * 60)
    logger.info(f"URL Base: {API_BASE_URL}")
    logger.info("")
    
    if run_batch:
        # Ejecutar pruebas batch de F30
        batch_results = test_certificado_f30_batch()
        if not batch_results:
            return 1
        
        all_passed = all(batch_results.values())
        total = len(batch_results)
        passed = sum(batch_results.values())
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("RESUMEN FINAL")
        logger.info("=" * 60)
        logger.info(f"Total documentos: {total}")
        logger.info(f"Exitosos: {passed}")
        logger.info(f"Fallidos: {total - passed}")
        
        if all_passed:
            logger.info("\n✓ Todas las pruebas pasaron correctamente")
        else:
            logger.error(f"\n✗ {total - passed} prueba(s) fallaron")
        
        return 0 if all_passed else 1
    else:
        # Ejecutar pruebas individuales
        results = {
            #"Etiqueta Walmart": test_with_result_check("etiqueta_walmart", test_etiqueta_walmart),
            #"Etiqueta ENVIAME": test_with_result_check("etiqueta_enviame", test_etiqueta_enviame),
            "Certificado F30 - Razón Social": test_with_result_check("certificado_f30_razon_social", test_certificado_f30),
            "Certificado F30 - Persona Natural": test_with_result_check("certificado_f30_persona_natural", test_certificado_f30_persona_natural),
        }
        
        logger.info("=" * 60)
        logger.info("RESUMEN DE PRUEBAS")
        logger.info("=" * 60)
        
        for endpoint, success in results.items():
            status = "✓ PASÓ" if success else "✗ FALLÓ"
            logger.info(f"{endpoint}: {status}")
        
        all_passed = all(results.values())
        
        if all_passed:
            logger.info("\n✓ Todas las pruebas pasaron correctamente")
        else:
            logger.error("\n✗ Algunas pruebas fallaron")
        
        logger.info("\nNota: Para probar múltiples documentos, ejecuta sin --single")
        logger.info("Ejemplo: python test_new_endpoints.py")
        
        return 0 if all_passed else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

