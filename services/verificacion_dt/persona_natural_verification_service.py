"""
Servicio para verificar y descargar certificados F30 de Persona Natural
en el portal oficial de la Dirección del Trabajo
http://tramites.dt.gob.cl/tramitesenlinea/VerificadorTramites/VerificadorTramites.aspx

Este servicio automatiza la verificación y descarga de certificados F30 para personas naturales.
"""

import logging
import time
from typing import Dict, Any, Optional
from pathlib import Path
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext

logger = logging.getLogger(__name__)


class PersonaNaturalVerificationService:
    """Servicio para verificar y descargar certificados F30 de Persona Natural"""
    
    PORTAL_URL = "http://tramites.dt.gob.cl/tramitesenlinea/VerificadorTramites/VerificadorTramites.aspx"
    
    # Selectores XPath identificados
    SELECTORS = {
        "tipo_tramite_select": "/html/body/form/div[3]/div[3]/div[3]/div[2]/table/tbody/tr[1]/td[2]/select",
        "tipo_tramite_select_id": "ctl00_cphTramite_ddlTipoTramite",
        "folio_oficina_input": "/html/body/form/div[3]/div[3]/div[3]/div[2]/table/tbody/tr[2]/td[2]/input[1]",
        "folio_oficina_input_id": "ctl00_cphTramite_tbICT",
        "folio_anio_input": "/html/body/form/div[3]/div[3]/div[3]/div[2]/table/tbody/tr[2]/td[2]/input[2]",
        "folio_anio_input_id": "ctl00_cphTramite_tbAgno",
        "folio_numero_input": "/html/body/form/div[3]/div[3]/div[3]/div[2]/table/tbody/tr[2]/td[2]/input[3]",
        "folio_numero_input_id": "ctl00_cphTramite_tbCorre",
        "codigo_verificacion_input": "/html/body/form/div[3]/div[3]/div[3]/div[2]/table/tbody/tr[3]/td[2]/input",
        "codigo_verificacion_input_id": "ctl00_cphTramite_tbCodVerificacion",
        "boton_buscar": "ctl00_cphTramite_btnBuscar",
        "mensaje_validacion": "ctl00_cphTramite_lblMensaje",
        "boton_descarga": "ctl00_cphTramite_ibtnHTMLC2"
    }
    
    TIPO_TRAMITE_VALUE = "2"  # ANTECEDENTES LABORALES Y PREVISIONALES
    
    def __init__(self, headless: bool = True, download_dir: Optional[str] = None, max_retries: int = 3):
        """
        Inicializa el servicio de verificación
        
        Args:
            headless: Si True, ejecuta el navegador en modo headless
            download_dir: Directorio donde guardar descargas (opcional)
            max_retries: Número máximo de reintentos en caso de error
        """
        self.headless = headless
        self.download_dir = download_dir or str(Path.cwd() / "downloads")
        self.max_retries = max_retries
        Path(self.download_dir).mkdir(parents=True, exist_ok=True)
    
    def verify_and_download(
        self,
        folio_oficina: str,
        folio_anio: str,
        folio_numero_consecutivo: str,
        codigo_verificacion: str,
        timeout: int = 60
    ) -> Dict[str, Any]:
        """
        Verifica y descarga un certificado F30 de Persona Natural
        
        Args:
            folio_oficina: Código de la Inspección/Oficina (ej: "2000")
            folio_anio: Año del folio (ej: "2025")
            folio_numero_consecutivo: Número consecutivo del folio (ej: "424494")
            codigo_verificacion: Código alfanumérico de verificación (ej: "T1z57kA1")
            timeout: Tiempo máximo de espera en segundos
        
        Returns:
            Dict con:
            - success: bool - Si la operación fue exitosa
            - valid: bool - Si el certificado es válido
            - message: str - Mensaje descriptivo
            - downloaded_file: Optional[str] - Ruta del archivo descargado si es válido
            - error: Optional[str] - Mensaje de error si hubo problema
            - folios_ingresados: Dict - Folios que se intentaron ingresar
        """
        folios_ingresados = {
            "folio_oficina": folio_oficina,
            "folio_anio": folio_anio,
            "folio_numero_consecutivo": folio_numero_consecutivo,
            "codigo_verificacion": codigo_verificacion
        }
        
        logger.info(f"Iniciando verificación de certificado F30 Persona Natural con folios: {folios_ingresados}")
        
        # Reintentos en caso de error
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"Intento {attempt} de {self.max_retries}")
                result = self._execute_verification(
                    folio_oficina,
                    folio_anio,
                    folio_numero_consecutivo,
                    codigo_verificacion,
                    timeout,
                    folios_ingresados
                )
                
                if result["success"]:
                    return result
                else:
                    last_error = result.get("error", "Error desconocido")
                    logger.warning(f"Intento {attempt} falló: {last_error}")
                    if attempt < self.max_retries:
                        time.sleep(2)  # Esperar antes de reintentar
                
            except Exception as e:
                last_error = str(e)
                logger.error(f"Error en intento {attempt}: {e}", exc_info=True)
                if attempt < self.max_retries:
                    time.sleep(2)
        
        # Si todos los intentos fallaron
        logger.error(f"Todos los intentos fallaron. Último error: {last_error}")
        return {
            "success": False,
            "valid": False,
            "message": "Error después de múltiples intentos",
            "downloaded_file": None,
            "error": last_error,
            "folios_ingresados": folios_ingresados
        }
    
    def _execute_verification(
        self,
        folio_oficina: str,
        folio_anio: str,
        folio_numero_consecutivo: str,
        codigo_verificacion: str,
        timeout: int,
        folios_ingresados: Dict[str, str]
    ) -> Dict[str, Any]:
        """Ejecuta la verificación en el portal"""
        
        browser = None
        context = None
        page = None
        
        try:
            with sync_playwright() as playwright:
                # Configurar navegador con descargas y argumentos para Cloud Run
                browser = playwright.chromium.launch(
                    headless=True,  # Siempre headless en Cloud Run
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',  # Importante para contenedores
                        '--disable-gpu',  # No hay GPU en Cloud Run
                        '--disable-software-rasterizer',
                        '--disable-extensions',
                        '--disable-background-networking',
                        '--disable-background-timer-throttling',
                        '--disable-backgrounding-occluded-windows',
                        '--disable-breakpad',
                        '--disable-component-extensions-with-background-pages',
                        '--disable-default-apps',
                        '--disable-features=TranslateUI',
                        '--disable-hang-monitor',
                        '--disable-ipc-flooding-protection',
                        '--disable-prompt-on-repost',
                        '--disable-renderer-backgrounding',
                        '--disable-sync',
                        '--force-color-profile=srgb',
                        '--metrics-recording-only',
                        '--no-first-run',
                        '--enable-automation',
                        '--enable-features=NetworkService,NetworkServiceInProcess',
                        '--password-store=basic',
                        '--use-mock-keychain',
                        '--window-size=1920,1080',
                    ]
                )
                
                # Crear contexto con descargas habilitadas
                context = browser.new_context(
                    accept_downloads=True,
                    viewport={'width': 1920, 'height': 1080}
                )
                
                page = context.new_page()
                
                # Configurar listener para descargas
                downloaded_file_path = None
                download_event = {"triggered": False}
                
                def handle_download(download):
                    nonlocal downloaded_file_path
                    download_event["triggered"] = True
                    timestamp = int(time.time())
                    filename = f"f30_persona_natural_{folio_oficina}_{folio_anio}_{folio_numero_consecutivo}_{timestamp}.pdf"
                    file_path = Path(self.download_dir) / filename
                    try:
                        download.save_as(str(file_path))
                        downloaded_file_path = str(file_path)
                        logger.info(f"Archivo descargado: {downloaded_file_path}")
                    except Exception as e:
                        logger.error(f"Error al guardar descarga: {e}")
                
                page.on("download", handle_download)
                
                # Navegar al portal
                logger.info(f"Navegando a {self.PORTAL_URL}")
                page.goto(self.PORTAL_URL, wait_until="domcontentloaded", timeout=timeout * 1000)
                
                # Esperar a que la página cargue
                logger.info("Esperando carga del formulario...")
                time.sleep(2)
                
                # Seleccionar tipo de trámite: ANTECEDENTES LABORALES Y PREVISIONALES
                logger.info("Seleccionando tipo de trámite...")
                tipo_tramite_select = page.locator(f"#{self.SELECTORS['tipo_tramite_select_id']}")
                tipo_tramite_select.wait_for(state="visible", timeout=15000)
                tipo_tramite_select.select_option(self.TIPO_TRAMITE_VALUE)
                time.sleep(1)  # Esperar a que se actualice el formulario
                
                # Ingresar folio_oficina
                logger.info(f"Ingresando folio_oficina: {folio_oficina}")
                folio_oficina_input = page.locator(f"#{self.SELECTORS['folio_oficina_input_id']}")
                folio_oficina_input.wait_for(state="visible", timeout=10000)
                folio_oficina_input.clear()
                folio_oficina_input.fill(folio_oficina)
                time.sleep(0.5)
                
                # Ingresar folio_anio
                logger.info(f"Ingresando folio_anio: {folio_anio}")
                folio_anio_input = page.locator(f"#{self.SELECTORS['folio_anio_input_id']}")
                folio_anio_input.wait_for(state="visible", timeout=10000)
                folio_anio_input.clear()
                folio_anio_input.fill(folio_anio)
                time.sleep(0.5)
                
                # Ingresar folio_numero_consecutivo
                logger.info(f"Ingresando folio_numero_consecutivo: {folio_numero_consecutivo}")
                folio_numero_input = page.locator(f"#{self.SELECTORS['folio_numero_input_id']}")
                folio_numero_input.wait_for(state="visible", timeout=10000)
                folio_numero_input.clear()
                folio_numero_input.fill(folio_numero_consecutivo)
                time.sleep(0.5)
                
                # Ingresar codigo_verificacion
                logger.info(f"Ingresando codigo_verificacion: {codigo_verificacion}")
                codigo_input = page.locator(f"#{self.SELECTORS['codigo_verificacion_input_id']}")
                codigo_input.wait_for(state="visible", timeout=10000)
                codigo_input.clear()
                codigo_input.fill(codigo_verificacion)
                time.sleep(0.5)
                
                # Presionar botón Buscar
                logger.info("Presionando botón Buscar...")
                boton_buscar = page.locator(f"#{self.SELECTORS['boton_buscar']}")
                boton_buscar.wait_for(state="visible", timeout=10000)
                boton_buscar.click()
                
                # Esperar respuesta
                logger.info("Esperando respuesta del portal...")
                time.sleep(3)
                
                # Verificar mensaje de validación
                mensaje_element = page.locator(f"#{self.SELECTORS['mensaje_validacion']}")
                mensaje_visible = mensaje_element.is_visible(timeout=10000)
                
                portal_message = None
                if mensaje_visible:
                    portal_message = mensaje_element.inner_text()
                    logger.info(f"Mensaje del portal: {portal_message}")
                    
                    # Verificar si dice "El certificado es VALIDO"
                    if "VALIDO" in portal_message.upper() or "VÁLIDO" in portal_message.upper():
                        logger.info("Certificado válido, intentando descargar...")
                        
                        # Presionar botón de descarga
                        boton_descarga = page.locator(f"#{self.SELECTORS['boton_descarga']}")
                        if boton_descarga.is_visible(timeout=5000):
                            boton_descarga.click()
                            
                            # Esperar descarga
                            max_wait_download = 15
                            wait_interval = 0.5
                            waited = 0
                            
                            while waited < max_wait_download:
                                if downloaded_file_path and Path(downloaded_file_path).exists():
                                    file_size = Path(downloaded_file_path).stat().st_size
                                    if file_size > 0:
                                        logger.info(f"Certificado válido. Archivo descargado: {downloaded_file_path} ({file_size} bytes)")
                                        return {
                                            "success": True,
                                            "valid": True,
                                            "message": "Certificado válido - Documento descargado",
                                            "downloaded_file": downloaded_file_path,
                                            "portal_message": portal_message,
                                            "error": None,
                                            "folios_ingresados": folios_ingresados
                                        }
                                time.sleep(wait_interval)
                                waited += wait_interval
                            
                            # Si no se descargó pero el mensaje dice válido
                            if download_event["triggered"]:
                                return {
                                    "success": True,
                                    "valid": True,
                                    "message": "Certificado válido (descarga en proceso)",
                                    "downloaded_file": downloaded_file_path,
                                    "portal_message": portal_message,
                                    "error": None,
                                    "folios_ingresados": folios_ingresados
                                }
                            else:
                                return {
                                    "success": False,
                                    "valid": True,
                                    "message": "Certificado válido pero no se pudo descargar",
                                    "downloaded_file": None,
                                    "portal_message": portal_message,
                                    "error": "No se detectó descarga después de presionar botón",
                                    "folios_ingresados": folios_ingresados
                                }
                    else:
                        # Certificado no válido
                        logger.warning(f"Certificado no válido: {portal_message}")
                        return {
                            "success": True,
                            "valid": False,
                            "message": "Certificado no válido",
                            "error_message": portal_message,
                            "portal_message": portal_message,
                            "downloaded_file": None,
                            "error": None,
                            "folios_ingresados": folios_ingresados
                        }
                else:
                    # No se encontró mensaje de validación
                    logger.warning("No se encontró mensaje de validación en la página")
                    return {
                        "success": False,
                        "valid": False,
                        "message": "No se pudo determinar el resultado",
                        "downloaded_file": None,
                        "portal_message": None,
                        "error": "No se encontró mensaje de validación después de buscar",
                        "folios_ingresados": folios_ingresados
                    }
                
        except Exception as e:
            logger.error(f"Error durante la verificación: {e}", exc_info=True)
            return {
                "success": False,
                "valid": False,
                "message": "Error durante la verificación",
                "downloaded_file": None,
                "portal_message": None,
                "error": str(e),
                "folios_ingresados": folios_ingresados
            }
        
        finally:
            # Cerrar recursos en orden inverso
            try:
                if page:
                    page.close()
            except Exception as e:
                logger.warning(f"Error al cerrar página: {e}")
            
            try:
                if context:
                    context.close()
            except Exception as e:
                logger.warning(f"Error al cerrar contexto: {e}")
            
            try:
                if browser:
                    browser.close()
            except Exception as e:
                logger.warning(f"Error al cerrar navegador: {e}")

