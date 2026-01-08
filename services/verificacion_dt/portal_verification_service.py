"""
Servicio para verificar códigos de certificados en el portal oficial de la Dirección del Trabajo
https://midt.dirtrab.cl/verificadorDocumental

Este servicio está aislado para pruebas antes de integrarlo en el pipeline principal.
"""

import logging
import time
import os
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
from playwright_recaptcha import recaptchav2

logger = logging.getLogger(__name__)


class PortalVerificationService:
    """Servicio para verificar códigos de certificados en el portal oficial"""
    
    PORTAL_URL = "https://midt.dirtrab.cl/verificadorDocumental"
    
    # Selectores identificados
    SELECTORS = {
        "codigo_input": "#codigoVerificacionId",
        "codigo_input_name": "codigoVerificacion",
        "boton_verificar": "button:has-text('Verificar')",
        "mensaje_error": ".ui.error.bottom.attached.message",
        "recaptcha": ".recaptcha-checkbox-border"
    }
    
    def __init__(
        self, 
        headless: bool = True, 
        download_dir: Optional[str] = None
    ):
        """
        Inicializa el servicio de verificación
        
        Args:
            headless: Si True, ejecuta el navegador en modo headless
            download_dir: Directorio donde guardar descargas (opcional)
        """
        self.headless = headless
        self.download_dir = download_dir or str(Path.cwd() / "downloads")
        Path(self.download_dir).mkdir(parents=True, exist_ok=True)
    
    def verify_code(
        self, 
        codigo: str, 
        timeout: int = 90
    ) -> Dict[str, Any]:
        """
        Verifica un código de certificado en el portal oficial
        
        Args:
            codigo: Código del certificado a verificar (formato: "XXXX XXXX XXXX")
            timeout: Tiempo máximo de espera en segundos
        
        Returns:
            Dict con:
            - success: bool - Si la verificación fue exitosa
            - valid: bool - Si el código es válido
            - message: str - Mensaje descriptivo
            - downloaded_file: Optional[str] - Ruta del archivo descargado si es válido
            - error: Optional[str] - Mensaje de error si hubo problema
        """
        logger.info(f"Iniciando verificación de código: {codigo}")
        
        browser = None
        context = None
        page = None
        
        try:
            with sync_playwright() as playwright:
                # Configurar argumentos del navegador
                browser_args = [
                    '--no-sandbox', 
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',  # Importante para contenedores (evita problemas de memoria compartida)
                ]
                
                # Configurar argumentos según el modo
                if self.headless:
                    # Modo headless: argumentos optimizados para Cloud Run
                    browser_args.extend([
                        '--window-size=1920,1080',
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
                    ])
                else:
                    # Modo visible: maximizar ventana
                    browser_args.append('--start-maximized')
                
                # Configurar navegador con descargas y argumentos
                browser = playwright.chromium.launch(
                    headless=self.headless,  # Usar el parámetro del constructor
                    args=browser_args
                )
                
                # Crear contexto con descargas habilitadas
                if self.headless:
                    # En modo headless, usar viewport fijo
                    context = browser.new_context(
                        accept_downloads=True,
                        viewport={'width': 1920, 'height': 1080}
                    )
                else:
                    # En modo visible, no usar viewport fijo para permitir maximización
                    context = browser.new_context(
                        accept_downloads=True,
                        no_viewport=True  # Permite que la ventana se maximice correctamente
                    )
                
                page = context.new_page()
                
                # Configurar listener para descargas
                downloaded_file_path = None
                download_event = {"triggered": False, "link_clicked": False}
                
                def handle_download(download):
                    nonlocal downloaded_file_path
                    logger.info("🔄 Evento de descarga detectado!")
                    download_event["triggered"] = True
                    
                    try:
                        # Obtener información de la descarga
                        suggested_filename = download.suggested_filename
                        logger.info(f"Nombre sugerido del archivo: {suggested_filename}")
                        logger.info(f"URL de descarga: {download.url}")
                        
                        # Generar nombre único para el archivo
                        timestamp = int(time.time())
                        # Limpiar código para nombre de archivo
                        codigo_limpio = codigo.replace(' ', '_').replace('-', '_')
                        
                        # Usar el nombre sugerido si es PDF, sino usar el nombre generado
                        if suggested_filename and suggested_filename.endswith('.pdf'):
                            filename = f"certificado_{codigo_limpio}_{timestamp}_{suggested_filename}"
                        else:
                            filename = f"certificado_{codigo_limpio}_{timestamp}.pdf"
                        
                        file_path = Path(self.download_dir) / filename
                        logger.info(f"Guardando archivo en: {file_path}")
                        
                        download.save_as(str(file_path))
                        downloaded_file_path = str(file_path)
                        
                        # Verificar que el archivo se guardó correctamente
                        if Path(downloaded_file_path).exists():
                            file_size = Path(downloaded_file_path).stat().st_size
                            logger.info(f"✅ Archivo descargado exitosamente: {downloaded_file_path} ({file_size} bytes)")
                        else:
                            logger.error(f"❌ El archivo no existe después de guardar: {downloaded_file_path}")
                    except Exception as e:
                        logger.error(f"❌ Error al guardar descarga: {e}", exc_info=True)
                
                page.on("download", handle_download)
                logger.info("Listener de descarga configurado")
                
                # Navegar al portal con estrategia más robusta para páginas lentas
                logger.info(f"Navegando a {self.PORTAL_URL}")
                try:
                    # Intentar primero con domcontentloaded (más rápido)
                    page.goto(self.PORTAL_URL, wait_until="domcontentloaded", timeout=timeout * 1000)
                except Exception as nav_error:
                    # Si falla, intentar con "load" que espera más recursos
                    logger.warning(f"domcontentloaded falló, intentando con 'load': {nav_error}")
                    try:
                        page.goto(self.PORTAL_URL, wait_until="load", timeout=timeout * 1000)
                    except Exception as load_error:
                        # Si también falla, intentar sin wait_until específico
                        logger.warning(f"'load' también falló, intentando sin wait_until: {load_error}")
                        page.goto(self.PORTAL_URL, timeout=timeout * 1000)
                
                # Esperar explícitamente a que el input sea visible (esto asegura que la app cargó)
                logger.info("Esperando carga del formulario...")
                codigo_input = page.locator(self.SELECTORS["codigo_input"])
                # Aumentar timeout para esperar el input (puede tardar más en Cloud Run)
                codigo_input.wait_for(state="visible", timeout=30000)  # 30 segundos
                
                time.sleep(2)  # Pequeña pausa para asegurar que todo está cargado
                
                # Ingresar código
                logger.info(f"Ingresando código: {codigo}")
                codigo_input = page.locator(self.SELECTORS["codigo_input"])
                codigo_input.wait_for(state="visible", timeout=10000)
                codigo_input.clear()
                codigo_input.fill(codigo)
                
                # Esperar un momento para que el input se actualice
                time.sleep(0.5)
                
                # Resolver reCAPTCHA si está presente
                logger.info("Verificando presencia de reCAPTCHA...")
                recaptcha_resuelto = False
                recaptcha_error_msg = None
                try:
                    # Intentar resolver reCAPTCHA
                    with recaptchav2.SyncSolver(page) as solver:
                        logger.info("Resolviendo reCAPTCHA...")
                        token = solver.solve_recaptcha(wait=True)
                        logger.info("reCAPTCHA resuelto exitosamente")
                        recaptcha_resuelto = True
                except Exception as recaptcha_error:
                    recaptcha_error_msg = str(recaptcha_error)
                    # Si no hay reCAPTCHA o ya está resuelto, continuar
                    logger.warning(f"No se pudo resolver reCAPTCHA o no está presente: {recaptcha_error}")
                    # Verificar si el reCAPTCHA ya está marcado
                    try:
                        recaptcha_checked = page.locator(".recaptcha-checkbox-checked").count()
                        if recaptcha_checked > 0:
                            logger.info("reCAPTCHA ya estaba resuelto")
                            recaptcha_resuelto = True
                        else:
                            # Verificar si es rate limit
                            if "rate limit" in recaptcha_error_msg.lower():
                                logger.error("Rate limit de reCAPTCHA excedido. No se puede continuar.")
                                raise Exception(f"Rate limit de reCAPTCHA excedido. Error: {recaptcha_error_msg}")
                            logger.warning("reCAPTCHA no resuelto, pero continuando...")
                    except Exception as check_error:
                        # Si es rate limit, lanzar error
                        if recaptcha_error_msg and "rate limit" in recaptcha_error_msg.lower():
                            raise Exception(f"Rate limit de reCAPTCHA excedido. Error: {recaptcha_error_msg}")
                        pass
                
                # Hacer clic en el botón Verificar
                logger.info("Haciendo clic en botón Verificar...")
                boton_verificar = page.locator(self.SELECTORS["boton_verificar"])
                boton_verificar.wait_for(state="visible", timeout=10000)
                
                # Esperar a que el botón esté habilitado (no disabled)
                logger.info("Esperando a que el botón esté habilitado...")
                try:
                    # Esperar hasta 30 segundos a que el botón se habilite
                    boton_verificar.wait_for(
                        state="visible",
                        timeout=30000
                    )
                    # Verificar que no esté deshabilitado
                    is_disabled = boton_verificar.get_attribute("disabled")
                    if is_disabled is not None:
                        logger.info("Botón está deshabilitado, esperando a que se habilite...")
                        # Esperar a que el atributo disabled desaparezca usando selector más simple
                        try:
                            # Intentar esperar usando el selector por clase
                            page.wait_for_function(
                                "() => { const btn = document.querySelector('button.ui.green.medium.icon.right.labeled.button'); return btn && !btn.disabled; }",
                                timeout=30000
                            )
                            logger.info("Botón habilitado")
                        except Exception as wait_error:
                            logger.warning(f"Error esperando botón habilitado: {wait_error}")
                            # Intentar esperar un poco más y verificar manualmente
                            time.sleep(5)
                            is_disabled_after = boton_verificar.get_attribute("disabled")
                            if is_disabled_after is not None:
                                logger.warning("Botón sigue deshabilitado después de esperar. Posible problema con reCAPTCHA.")
                                raise Exception("Botón de verificación no se habilitó. Posible problema con reCAPTCHA o rate limit.")
                except Exception as e:
                    logger.warning(f"Timeout esperando botón habilitado: {e}")
                    # Si el botón no se habilita, puede ser por rate limit del reCAPTCHA
                    raise Exception(f"No se pudo habilitar el botón de verificación. Posible rate limit de reCAPTCHA: {str(e)}")
                
                boton_verificar.click()
                
                # Esperar respuesta (puede ser descarga o mensaje de error)
                logger.info("Esperando respuesta del portal...")
                time.sleep(3)  # Esperar inicial
                
                # Verificar si hay mensaje de error
                mensaje_error = page.locator(self.SELECTORS["mensaje_error"])
                error_visible = mensaje_error.is_visible(timeout=5000)
                
                portal_message = None
                if error_visible:
                    portal_message = mensaje_error.inner_text()
                    logger.warning(f"Código inválido: {portal_message}")
                    return {
                        "success": True,  # La verificación fue exitosa técnicamente
                        "valid": False,
                        "message": "Código inválido",
                        "error_message": portal_message,
                        "portal_message": portal_message,
                        "downloaded_file": None,
                        "error": None
                    }
                
                # Si no hay error, verificar si se descargó un archivo
                # Esperar hasta 30 segundos por la descarga (aumentado para dar más tiempo)
                max_wait_download = 30
                wait_interval = 0.5
                waited = 0
                
                logger.info(f"Esperando descarga (máximo {max_wait_download} segundos)...")
                
                while waited < max_wait_download:
                    # Verificar si se activó el evento de descarga
                    if download_event["triggered"]:
                        logger.info("Evento de descarga detectado")
                    
                    # Verificar si el archivo existe y tiene contenido
                    if downloaded_file_path and Path(downloaded_file_path).exists():
                        file_size = Path(downloaded_file_path).stat().st_size
                        if file_size > 0:  # Asegurar que el archivo no esté vacío
                            logger.info(f"Código válido. Archivo descargado: {downloaded_file_path} ({file_size} bytes)")
                            # Intentar obtener mensaje del portal si está disponible
                            try:
                                page_content = page.content()
                                if "válido" in page_content.lower() or "valido" in page_content.lower():
                                    portal_message = "Archivo válido"
                                else:
                                    portal_message = None
                            except:
                                portal_message = None
                            
                            return {
                                "success": True,
                                "valid": True,
                                "message": "Código válido - Documento descargado",
                                "downloaded_file": downloaded_file_path,
                                "portal_message": portal_message,
                                "error": None
                            }
                    
                    # Verificar si hay enlaces de descarga en la página (solo una vez)
                    if waited > 2 and not download_event.get("link_clicked", False):  # Esperar un poco y solo intentar una vez
                        try:
                            # Buscar enlaces de descarga más específicos
                            download_links = page.locator("a[href*='.pdf'], a[download], button[onclick*='download'], a[href*='download'], .download-link, [class*='download']").all()
                            if download_links:
                                logger.info(f"Se encontraron {len(download_links)} posibles enlaces de descarga")
                                # Intentar hacer clic en el primer enlace de descarga visible y habilitado
                                for link in download_links:
                                    try:
                                        # Verificar que el enlace sea visible y clickeable
                                        if not link.is_visible(timeout=1000):
                                            continue
                                        
                                        href = link.get_attribute("href")
                                        text = link.inner_text()
                                        logger.info(f"Enlace encontrado - href: {href}, text: {text[:50]}")
                                        
                                        # Intentar descargar
                                        logger.info(f"Intentando hacer clic en enlace de descarga...")
                                        with page.expect_download(timeout=15000) as download_info:
                                            link.click()
                                        download = download_info.value
                                        timestamp = int(time.time())
                                        codigo_limpio = codigo.replace(' ', '_').replace('-', '_')
                                        filename = f"certificado_{codigo_limpio}_{timestamp}.pdf"
                                        file_path = Path(self.download_dir) / filename
                                        download.save_as(str(file_path))
                                        downloaded_file_path = str(file_path)
                                        download_event["link_clicked"] = True
                                        logger.info(f"✅ Archivo descargado desde enlace: {downloaded_file_path}")
                                        break
                                    except Exception as link_error:
                                        logger.debug(f"Error al intentar descargar desde enlace: {link_error}")
                                        continue
                                
                                # Marcar que ya intentamos hacer clic
                                if download_links:
                                    download_event["link_clicked"] = True
                        except Exception as e:
                            logger.debug(f"Error al buscar enlaces de descarga: {e}")
                    
                    time.sleep(wait_interval)
                    waited += wait_interval
                    
                    # Log cada 5 segundos para mostrar progreso
                    if int(waited) % 5 == 0 and waited > 0:
                        logger.info(f"Esperando descarga... ({int(waited)}/{max_wait_download} segundos)")
                
                # Verificación final: buscar archivos descargados en el directorio
                if not downloaded_file_path:
                    logger.info("Buscando archivos descargados en el directorio...")
                    try:
                        # Buscar archivos PDF recientes en el directorio de descargas
                        download_dir_path = Path(self.download_dir)
                        if download_dir_path.exists():
                            # Buscar archivos PDF modificados en los últimos 60 segundos
                            current_time = time.time()
                            for file_path in download_dir_path.glob("*.pdf"):
                                try:
                                    file_mtime = file_path.stat().st_mtime
                                    if current_time - file_mtime < 60:  # Archivo modificado en último minuto
                                        file_size = file_path.stat().st_size
                                        if file_size > 0:
                                            logger.info(f"Archivo encontrado en directorio: {file_path} ({file_size} bytes)")
                                            downloaded_file_path = str(file_path)
                                            break
                                except Exception as e:
                                    logger.debug(f"Error al verificar archivo {file_path}: {e}")
                    except Exception as e:
                        logger.debug(f"Error al buscar archivos en directorio: {e}")
                
                # Si se detectó evento de descarga pero no se guardó el archivo
                if download_event["triggered"] and not downloaded_file_path:
                    logger.warning("Se detectó descarga pero no se pudo guardar el archivo")
                
                # Si finalmente tenemos un archivo descargado, retornar éxito
                if downloaded_file_path and Path(downloaded_file_path).exists():
                    file_size = Path(downloaded_file_path).stat().st_size
                    if file_size > 0:
                        logger.info(f"Archivo descargado encontrado: {downloaded_file_path} ({file_size} bytes)")
                        return {
                            "success": True,
                            "valid": True,
                            "message": "Código válido - Documento descargado",
                            "downloaded_file": downloaded_file_path,
                            "portal_message": "Archivo válido",
                            "error": None
                        }
                
                # Si no hay error ni descarga, algo inesperado pasó
                logger.warning("No se detectó ni error ni descarga. Verificando estado de la página...")
                page_content = page.content()
                
                # Verificar si hay algún mensaje de éxito o estado
                if "verificado" in page_content.lower() or "válido" in page_content.lower():
                    portal_message = "Archivo válido"
                    return {
                        "success": True,
                        "valid": True,
                        "message": "Código válido (sin descarga detectada)",
                        "downloaded_file": None,
                        "portal_message": portal_message,
                        "error": None
                    }
                
                return {
                    "success": False,
                    "valid": False,
                    "message": "No se pudo determinar el resultado",
                    "downloaded_file": None,
                    "portal_message": None,
                    "error": "No se detectó ni error ni descarga después de la verificación"
                }
                
        except Exception as e:
            logger.error(f"Error durante la verificación: {e}", exc_info=True)
            return {
                "success": False,
                "valid": False,
                "message": "Error durante la verificación",
                "downloaded_file": None,
                "portal_message": None,
                "error": str(e)
            }
        
        finally:
            # Cerrar recursos en orden inverso
            # Usar try-except para manejar casos donde el event loop ya está cerrado
            try:
                if page:
                    page.close()
            except Exception as e:
                # Ignorar errores de "Event loop is closed" ya que Playwright ya se cerró
                error_str = str(e).lower()
                if "event loop is closed" not in error_str and "already stopped" not in error_str:
                    logger.warning(f"Error al cerrar página: {e}")
            
            try:
                if context:
                    context.close()
            except Exception as e:
                # Ignorar errores de "Event loop is closed"
                error_str = str(e).lower()
                if "event loop is closed" not in error_str and "already stopped" not in error_str:
                    logger.warning(f"Error al cerrar contexto: {e}")
            
            try:
                if browser:
                    browser.close()
            except Exception as e:
                # Ignorar errores de "Event loop is closed"
                error_str = str(e).lower()
                if "event loop is closed" not in error_str and "already stopped" not in error_str:
                    logger.warning(f"Error al cerrar navegador: {e}")
    
    def verify_code_simple(self, codigo: str) -> Tuple[bool, Optional[str]]:
        """
        Versión simplificada que solo retorna si es válido o no
        
        Returns:
            Tuple[bool, Optional[str]]: (es_valido, mensaje_error)
        """
        result = self.verify_code(codigo)
        
        if not result["success"]:
            return False, result.get("error", "Error desconocido")
        
        if result["valid"]:
            return True, None
        else:
            return False, result.get("error_message", "Código inválido")

