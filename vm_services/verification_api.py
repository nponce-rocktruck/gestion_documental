"""
API de Verificación para VM
Expone servicios de verificación usando undetected_chromedriver + 2captcha + Oxylabs
Basado en project_dt/test_oxylabs.py
"""

import os
import sys
import time
import json
import base64
import zipfile
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, Optional

import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth
import undetected_chromedriver as uc

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Silenciar logs de selenium-wire (muy verbosos)
logging.getLogger("seleniumwire.handler").setLevel(logging.WARNING)
logging.getLogger("seleniumwire.backend").setLevel(logging.WARNING)

# Configuración desde variables de entorno
OXY_USER = os.getenv("OXY_USER", "conirarra_FyqF8")
OXY_PASS = os.getenv("OXY_PASS", "Clemente_2011")
OXY_HOST = os.getenv("OXY_HOST", "unblock.oxylabs.io")
OXY_PORT = os.getenv("OXY_PORT", "60000")
API_KEY_2CAPTCHA = os.getenv("API_KEY_2CAPTCHA", "e716e4f00d5e2225bcd8ed2a04981fe3")

# Directorio para archivos temporales
TEMP_DIR = Path("/tmp/vm_verification")
TEMP_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="VM Verification API", version="1.0.0")
executor = ThreadPoolExecutor(max_workers=2)


# Modelos de request
class PortalDocumentalRequest(BaseModel):
    codigo: str


class PersonaNaturalRequest(BaseModel):
    folio_oficina: str
    folio_anio: str
    folio_numero: str
    codigo_verificacion: str


def crear_proxy_auth_extension(proxy_host: str, proxy_port: str, proxy_user: str, proxy_pass: str) -> str:
    """Crea extensión de Chrome para autenticación de proxy"""
    plugin_path = TEMP_DIR / "proxy_auth_plugin.zip"
    manifest_json = json.dumps({
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Oxylabs Proxy",
        "permissions": ["proxy", "tabs", "unlimitedStorage", "storage", "<all_urls>", "webRequest", "webRequestBlocking"],
        "background": {"scripts": ["background.js"]},
        "minimum_chrome_version": "22.0.0"
    })
    background_js = f"""
    var config = {{
        mode: "fixed_servers",
        rules: {{
            singleProxy: {{
                scheme: "http",
                host: "{proxy_host}",
                port: parseInt({proxy_port})
            }},
            bypassList: ["localhost"]
        }}
    }};
    chrome.proxy.settings.set({{value: config, scope: "regular"}}, function() {{}});
    chrome.webRequest.onAuthRequired.addListener(
        function(details) {{
            return {{
                authCredentials: {{
                    username: "{proxy_user}",
                    password: "{proxy_pass}"
                }}
            }};
        }},
        {{urls: ["<all_urls>"]}},
        ["blocking"]
    );
    """
    with zipfile.ZipFile(plugin_path, 'w') as zp:
        zp.writestr("manifest.json", manifest_json)
        zp.writestr("background.js", background_js)
    return str(plugin_path)


def resolver_captcha_2captcha() -> Optional[str]:
    """Resuelve reCAPTCHA usando 2captcha"""
    logger.info("Solicitando resolución a 2Captcha...")
    payload = {
        "clientKey": API_KEY_2CAPTCHA,
        "task": {
            "type": "RecaptchaV2TaskProxyless",
            "websiteURL": "https://midt.dirtrab.cl/verificadorDocumental",
            "websiteKey": "6LfHXbAUAAAAAABcvhixT8Cyu-7wSRVjh8pHjPnu",
            "isInvisible": False
        }
    }
    try:
        res = requests.post("https://api.2captcha.com/createTask", json=payload, timeout=30).json()
        if res.get("errorId") != 0:
            logger.error(f"Error en 2captcha createTask: {res}")
            return None
        task_id = res.get("taskId")
        
        max_attempts = 60  # 5 minutos máximo
        attempt = 0
        while attempt < max_attempts:
            time.sleep(5)
            status = requests.post(
                "https://api.2captcha.com/getTaskResult",
                json={"clientKey": API_KEY_2CAPTCHA, "taskId": task_id},
                timeout=30
            ).json()
            if status.get("status") == "ready":
                token = status.get("solution", {}).get("gRecaptchaResponse")
                logger.info("reCAPTCHA resuelto exitosamente")
                return token
            if status.get("errorId") != 0:
                logger.error(f"Error en 2captcha getTaskResult: {status}")
                return None
            attempt += 1
            if attempt % 6 == 0:
                logger.info(f"Esperando resolución de reCAPTCHA... ({attempt * 5}s)")
        logger.error("Timeout esperando resolución de reCAPTCHA")
        return None
    except Exception as e:
        logger.error(f"Error al resolver reCAPTCHA: {e}", exc_info=True)
        return None


def inyectar_token_captcha(driver, token: str):
    """Inyecta token de reCAPTCHA y ejecuta callback"""
    logger.info("Inyectando token de reCAPTCHA...")
    script_js = """
    var token = arguments[0];
    try {
        var area = document.getElementById('g-recaptcha-response');
        if (area) { area.value = token; area.innerHTML = token; }
        if (typeof (___grecaptcha_cfg) !== 'undefined') {
            for (let i in ___grecaptcha_cfg.clients) {
                let client = ___grecaptcha_cfg.clients[i];
                for (let prop in client) {
                    if (client[prop] && typeof client[prop].callback === 'function') {
                        client[prop].callback(token);
                    }
                }
            }
        }
    } catch (e) { console.error(e); }
    """
    driver.execute_script(script_js, token)
    driver.execute_script("""
        var t = arguments[0];
        var el = document.getElementById('g-recaptcha-response');
        if (el) {
            el.value = t;
            el.dispatchEvent(new Event('input', { bubbles: true }));
        }
    """, token)
    logger.info("Token inyectado exitosamente")


def verificar_portal_documental_sync(codigo: str) -> Dict[str, Any]:
    """Verifica código en portal documental y descarga PDF"""
    driver = None
    try:
        # Limpiar procesos anteriores
        os.system("pkill -f chromium > /dev/null 2>&1")
        time.sleep(1)
        
        # Crear extensión de proxy
        auth_extension = crear_proxy_auth_extension(OXY_HOST, OXY_PORT, OXY_USER, OXY_PASS)
        
        # Configurar Chrome
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument(f"--load-extension={auth_extension}")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-gpu")
        
        driver = webdriver.Chrome(options=options)
        driver.set_script_timeout(60)
        stealth(driver, languages=["es-CL", "es"], vendor="Google Inc.", platform="Win32", fix_hairline=True)
        
        driver.execute_cdp_cmd("Network.setExtraHTTPHeaders", {
            "headers": {
                "Origin": "https://midt.dirtrab.cl",
                "Referer": "https://midt.dirtrab.cl/"
            }
        })
        
        target_url = "https://midt.dirtrab.cl/verificadorDocumental"
        logger.info(f"Conectando vía Oxylabs a {target_url}...")
        driver.get(target_url)
        
        # Esperar a que cargue grecaptcha
        is_loaded = False
        for i in range(3):
            time.sleep(10)
            is_loaded = driver.execute_script("return typeof grecaptcha !== 'undefined';")
            if is_loaded:
                break
            driver.refresh()
        
        if not is_loaded:
            return {
                "success": False,
                "valid": False,
                "message": "No se pudo cargar grecaptcha",
                "error": "Timeout esperando carga de reCAPTCHA",
                "pdf_base64": None
            }
        
        # Resolver reCAPTCHA
        token = resolver_captcha_2captcha()
        if not token:
            return {
                "success": False,
                "valid": False,
                "message": "No se pudo resolver reCAPTCHA",
                "error": "Error al resolver reCAPTCHA con 2captcha",
                "pdf_base64": None
            }
        
        inyectar_token_captcha(driver, token)
        time.sleep(2)  # Esperar a que procese el token
        
        # Ingresar código y verificar
        logger.info(f"Verificando código: {codigo}")
        codigo_sin_espacios = codigo.replace(" ", "")
        
        # Script para ingresar código, hacer click y obtener PDF
        script_verificacion = f"""
        var callback = arguments[arguments.length - 1];
        var codigo = "{codigo_sin_espacios}";
        
        // Ingresar código
        var inputCodigo = document.querySelector('#codigoVerificacionId, input[name="codigoVerificacion"]');
        if (inputCodigo) {{
            inputCodigo.value = codigo;
            inputCodigo.dispatchEvent(new Event('input', {{ bubbles: true }}));
        }}
        
        // Esperar y hacer click en botón
        setTimeout(function() {{
            var btn = document.querySelector('button.ui.green.medium.icon.right.labeled.button');
            if (btn && !btn.disabled) {{
                btn.click();
                
                // Esperar respuesta
                setTimeout(function() {{
                    // Intentar obtener PDF desde la API
                    fetch("https://proxy-sso-portalinstitucional.api.dirtrab.cl/api/GestorDocumental/GetArchivoSerieDocumentalByIdentificadorSerieDocumental?identificadorSerieDocumental=" + codigo + "&isFirmadoRequerido=false", {{
                        "method": "GET",
                        "headers": {{
                            "Accept": "*/*",
                            "Origin": "https://midt.dirtrab.cl",
                            "Referer": "https://midt.dirtrab.cl/"
                        }}
                    }})
                    .then(r => {{
                        if (!r.ok) {{
                            callback({{valid: false, error: "Código inválido", pdf: null}});
                            return;
                        }}
                        return r.json();
                    }})
                    .then(data => {{
                        if (data && data.ArchivoBase64 && data.ArchivoBase64.length > 100) {{
                            callback({{valid: true, pdf: data.ArchivoBase64, error: null}});
                        }} else {{
                            callback({{valid: false, error: "Código inválido - no hay archivo", pdf: null}});
                        }}
                    }})
                    .catch(err => {{
                        callback({{valid: false, error: "Error en fetch: " + err.message, pdf: null}});
                    }});
                }}, 3000);
            }} else {{
                callback({{valid: false, error: "Botón no disponible", pdf: null}});
            }}
        }}, 2000);
        """
        
        resultado = driver.execute_async_script(script_verificacion)
        
        if resultado and resultado.get("valid"):
            pdf_base64 = resultado.get("pdf")
            return {
                "success": True,
                "valid": True,
                "message": "Código válido - PDF obtenido",
                "pdf_base64": pdf_base64,
                "error": None
            }
        else:
            error_msg = resultado.get("error", "Código inválido") if resultado else "Error desconocido"
            return {
                "success": True,
                "valid": False,
                "message": "Código inválido",
                "error_message": error_msg,
                "pdf_base64": None,
                "error": None
            }
            
    except Exception as e:
        logger.error(f"Error en verificación portal documental: {e}", exc_info=True)
        return {
            "success": False,
            "valid": False,
            "message": "Error durante la verificación",
            "error": str(e),
            "pdf_base64": None
        }
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass


def verificar_persona_natural_sync(folio_oficina: str, folio_anio: str, folio_numero: str, codigo_verificacion: str) -> Dict[str, Any]:
    """Verifica y descarga certificado F30 para persona natural"""
    # NOTA: Esta función requiere implementación completa
    # Por ahora retornamos error indicando que falta implementar
    return {
        "success": False,
        "valid": False,
        "message": "Verificación persona natural no implementada aún",
        "error": "Función pendiente de implementación",
        "pdf_base64": None
    }


@app.get("/")
async def root():
    return {"message": "VM Verification API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/verificar/portal-documental")
async def verificar_portal_documental(request: PortalDocumentalRequest):
    """Verifica código en portal documental y descarga PDF"""
    try:
        # Ejecutar en thread separado (Selenium es bloqueante)
        future = executor.submit(verificar_portal_documental_sync, request.codigo)
        result = future.result(timeout=180)  # 3 minutos máximo
        return result
    except Exception as e:
        logger.error(f"Error en endpoint portal-documental: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/verificar/persona-natural")
async def verificar_persona_natural(request: PersonaNaturalRequest):
    """Verifica y descarga certificado F30 para persona natural"""
    try:
        future = executor.submit(
            verificar_persona_natural_sync,
            request.folio_oficina,
            request.folio_anio,
            request.folio_numero,
            request.codigo_verificacion
        )
        result = future.result(timeout=180)
        return result
    except Exception as e:
        logger.error(f"Error en endpoint persona-natural: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

