"""
Servicio de OCR para la API de Documentos
Basado en Azure Computer Vision del proyecto original

Incluye un proveedor local basado en Tesseract para entornos sin Azure.
Selecciona proveedor mediante la variable de entorno OCR_PROVIDER: "azure" | "local" | "mock".
"""

import requests
import os
import io
import logging
from typing import Tuple, Optional
from urllib.parse import urlparse

from PIL import Image

try:
    import fitz  # PyMuPDF
except Exception:  # pragma: no cover
    fitz = None

try:
    import pytesseract
except Exception:  # pragma: no cover
    pytesseract = None

try:
    from google.cloud import vision, storage
    from google.oauth2 import service_account
except Exception:  # pragma: no cover
    vision = None
    storage = None
    service_account = None

logger = logging.getLogger(__name__)


class OCRService:
    """Servicio de OCR usando Azure Computer Vision"""
    
    def __init__(self):
        self.endpoint = os.getenv("AZURE_COMPUTER_VISION_ENDPOINT")
        self.api_key = os.getenv("AZURE_COMPUTER_VISION_API_KEY")
        
        if not self.endpoint or not self.api_key:
            raise ValueError("Azure Computer Vision no está configurado correctamente")
    
    def extract_text_from_url(self, file_url: str) -> Tuple[str, float]:
        """
        Extrae texto de un documento usando Azure Computer Vision
        
        Args:
            file_url: URL del documento a procesar
            
        Returns:
            Tuple[str, float]: (texto_extraido, costo_usd)
        """
        
        try:
            # Verificar que la URL sea accesible
            if not self._validate_url(file_url):
                raise ValueError("URL del documento no es válida o no es accesible")
            
            # Configurar headers para Azure Computer Vision
            headers = {
                'Ocp-Apim-Subscription-Key': self.api_key,
                'Content-Type': 'application/json'
            }
            
            # Configurar el cuerpo de la solicitud
            body = {
                'url': file_url
            }
            
            # URL del endpoint de OCR
            ocr_url = f"{self.endpoint}/vision/v3.2/read/analyze"
            
            # Realizar la solicitud inicial
            response = requests.post(ocr_url, headers=headers, json=body, timeout=30)
            response.raise_for_status()
            
            # Obtener la URL de resultado
            operation_url = response.headers.get('Operation-Location')
            if not operation_url:
                raise ValueError("No se recibió URL de operación de Azure")
            
            # Esperar y obtener el resultado
            text_result = self._wait_for_result(operation_url, headers)
            
            # Calcular costo (aproximado para Azure Computer Vision)
            cost = self._calculate_ocr_cost(len(text_result))
            
            return text_result, cost
            
        except requests.RequestException as e:
            logger.error(f"Error en solicitud a Azure Computer Vision: {e}")
            raise ValueError(f"Error al procesar documento: {str(e)}")
        except Exception as e:
            logger.error(f"Error inesperado en OCR: {e}")
            raise ValueError(f"Error inesperado: {str(e)}")
    
    def _validate_url(self, file_url: str) -> bool:
        """Valida que la URL sea accesible"""
        try:
            # Verificar que sea una URL válida
            parsed = urlparse(file_url)
            if not parsed.scheme or not parsed.netloc:
                return False
            
            # Verificar que sea accesible
            response = requests.head(file_url, timeout=10)
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Error al validar URL {file_url}: {e}")
            return False
    
    def _wait_for_result(self, operation_url: str, headers: dict, max_attempts: int = 30) -> str:
        """
        Espera y obtiene el resultado del OCR de Azure
        """
        import time
        
        for attempt in range(max_attempts):
            try:
                response = requests.get(operation_url, headers=headers, timeout=10)
                response.raise_for_status()
                
                result = response.json()
                status = result.get('status')
                
                if status == 'succeeded':
                    # Extraer texto de las líneas
                    text_lines = []
                    for read_result in result.get('analyzeResult', {}).get('readResults', []):
                        for line in read_result.get('lines', []):
                            text_lines.append(line.get('text', ''))
                    
                    return '\n'.join(text_lines)
                
                elif status == 'failed':
                    error_message = result.get('message', 'Error desconocido')
                    raise ValueError(f"OCR falló: {error_message}")
                
                # Si aún está procesando, esperar
                time.sleep(2)
                
            except requests.RequestException as e:
                logger.error(f"Error al obtener resultado (intento {attempt + 1}): {e}")
                if attempt == max_attempts - 1:
                    raise ValueError(f"Timeout al obtener resultado del OCR: {str(e)}")
                time.sleep(2)
        
        raise ValueError("Timeout: El OCR tardó demasiado en completarse")
    
    def _calculate_ocr_cost(self, text_length: int) -> float:
        """
        Calcula el costo aproximado del OCR
        Basado en los precios de Azure Computer Vision
        """
        # Precio aproximado: $1.50 por 1,000 transacciones
        # Asumimos que cada documento es una transacción
        base_cost = 0.0015  # $1.50 / 1000
        
        # Costo adicional por caracteres (muy pequeño)
        char_cost = (text_length / 1000000) * 0.01  # $0.01 por 1M caracteres
        
        return base_cost + char_cost


class MockOCRService:
    """Servicio de OCR mock para desarrollo y testing"""
    
    def extract_text_from_url(self, file_url: str) -> Tuple[str, float]:
        """
        Mock del servicio de OCR para desarrollo
        """
        logger.info(f"Mock OCR: Procesando {file_url}")
        
        # Simular texto extraído
        mock_text = """
        CERTIFICADO DE ANTECEDENTES
        
        Nombre: JUAN CARLOS PÉREZ GONZÁLEZ
        RUT: 12.345.678-9
        Fecha de Emisión: 15/01/2025
        
        No registra anotaciones
        
        Servicio de Registro Civil e Identificación
        """
        
        # Simular costo
        cost = 0.0015
        
        return mock_text.strip(), cost


class LocalOCRService:
    """Servicio de OCR local usando Tesseract (pytesseract) y PyMuPDF para PDFs."""

    def __init__(self):
        if pytesseract is None:
            raise ValueError("pytesseract no está instalado. Añádelo a requirements e instala Tesseract-OCREngine.")
        # PyMuPDF es opcional para PDFs; requerido si vas a procesar PDFs.
        self.has_pdf_support = fitz is not None
        # Permitir configurar ruta explícita al binario de Tesseract en Windows u otros entornos
        tesseract_cmd = os.getenv("TESSERACT_CMD")
        if tesseract_cmd:
            try:
                pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
            except Exception as e:
                logger.warning(f"No se pudo establecer TESSERACT_CMD='{tesseract_cmd}': {e}")

    def extract_text_from_url(self, file_url: str) -> Tuple[str, float]:
        """
        Extrae texto de una imagen o PDF obtenida por URL usando OCR local.
        Retorna (texto, costo_aprox).
        """
        if not self._validate_url(file_url):
            raise ValueError("URL del documento no es válida o no es accesible")

        try:
            # Convertir URL de Google Drive si es necesario
            download_url = self._convert_google_drive_url(file_url)
            logger.info(f"Descargando desde: {download_url}")
            
            resp = requests.get(download_url, timeout=60)
            resp.raise_for_status()
            content = resp.content
            
            # Validar que el contenido no esté vacío
            if not content:
                raise ValueError("El archivo descargado está vacío")
            
            # Determinar si es PDF por extensión o primeros bytes
            path = urlparse(file_url).path.lower()
            is_pdf = path.endswith(".pdf") or (len(content) >= 4 and content[:4] == b'%PDF')
            
            if is_pdf:
                if not self.has_pdf_support:
                    raise ValueError("PyMuPDF no está instalado y es requerido para PDFs")
                text = self._ocr_pdf(content)
            else:
                text = self._ocr_image(content)

            # Costo local: aproximación marginal casi cero, útil para trazabilidad
            cost = 0.0
            return text, cost
            
        except requests.RequestException as e:
            logger.error(f"Error al descargar archivo desde {file_url}: {e}")
            raise ValueError(f"Error al descargar el archivo: {str(e)}")
        except Exception as e:
            logger.error(f"Error al procesar archivo desde {file_url}: {e}")
            raise ValueError(f"Error al procesar el archivo: {str(e)}")

    def _ocr_image(self, image_bytes: bytes) -> str:
        try:
            # Validar que sea una imagen válida
            image = Image.open(io.BytesIO(image_bytes))
            # Verificar que se pueda convertir a RGB
            image = image.convert("RGB")
            # Config por defecto; se puede ajustar según idioma
            return pytesseract.image_to_string(image, lang=os.getenv("TESSERACT_LANG", "spa+eng"))
        except Exception as e:
            logger.error(f"Error al procesar imagen: {e}")
            raise ValueError(f"El archivo no es una imagen válida o está corrupto: {str(e)}")

    def _ocr_pdf(self, pdf_bytes: bytes) -> str:
        assert fitz is not None
        text_pages = []
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            for page in doc:
                pix = page.get_pixmap(dpi=200)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                page_text = pytesseract.image_to_string(img, lang=os.getenv("TESSERACT_LANG", "spa+eng"))
                text_pages.append(page_text)
        return "\n".join(text_pages)

    def _validate_url(self, file_url: str) -> bool:
        try:
            parsed = urlparse(file_url)
            if not parsed.scheme or not parsed.netloc:
                return False
            response = requests.head(file_url, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error al validar URL {file_url}: {e}")
            return False
    
    def _convert_google_drive_url(self, file_url: str) -> str:
        """Convierte enlace de Google Drive a enlace directo de descarga"""
        if "drive.google.com" in file_url:
            # Extraer ID del archivo
            if "/file/d/" in file_url:
                file_id = file_url.split("/file/d/")[1].split("/")[0]
                return f"https://drive.google.com/uc?export=download&id={file_id}"
        return file_url


class GCPOCRService:
    """Servicio de OCR usando Google Cloud Vision API"""
    
    def __init__(self):
        if vision is None or service_account is None:
            raise ValueError("Google Cloud Vision no está instalado. Instala google-cloud-vision")
        
        # Configurar credenciales de GCP
        self.project_id = os.getenv("GCP_PROJECT_ID")
        self.credentials_path = os.getenv("GCP_CREDENTIALS_PATH")
        self.credentials_json = os.getenv("GCP_CREDENTIALS_JSON")
        
        if not self.project_id:
            raise ValueError("GCP_PROJECT_ID no está configurado")
        
        # Configurar cliente de Vision API
        try:
            if self.credentials_path:
                # Usar archivo de credenciales
                credentials = service_account.Credentials.from_service_account_file(
                    self.credentials_path
                )
                self.client = vision.ImageAnnotatorClient(credentials=credentials)
            elif self.credentials_json:
                # Usar JSON de credenciales como string
                import json
                credentials_info = json.loads(self.credentials_json)
                credentials = service_account.Credentials.from_service_account_info(credentials_info)
                self.client = vision.ImageAnnotatorClient(credentials=credentials)
            else:
                # Usar credenciales por defecto (Application Default Credentials)
                self.client = vision.ImageAnnotatorClient()
        except Exception as e:
            raise ValueError(f"Error al configurar cliente de GCP Vision: {e}")
    
    def extract_text_from_url(self, file_url: str) -> Tuple[str, float]:
        """
        Extrae texto de un documento usando Google Cloud Vision API
        
        Args:
            file_url: URL del documento a procesar
            
        Returns:
            Tuple[str, float]: (texto_extraido, costo_usd)
        """
        
        try:
            # Verificar que la URL sea accesible
            if not self._validate_url(file_url):
                raise ValueError("URL del documento no es válida o no es accesible")
            
            # Convertir URL de Google Drive si es necesario
            download_url = self._convert_google_drive_url(file_url)
            if download_url != file_url:
                logger.info(f"URL convertida para descarga: {download_url}")
            
            # Descargar el archivo
            # Si es una URL de Google Cloud Storage, usar la librería de GCS
            if download_url.startswith("https://storage.googleapis.com/"):
                content = self._download_from_gcs(download_url)
            else:
                response = requests.get(download_url, timeout=60)
                response.raise_for_status()
                content = response.content
            
            # Validar que el contenido no esté vacío
            if not content:
                raise ValueError("El archivo descargado está vacío")
            
            # Determinar si es PDF por extensión o primeros bytes
            is_pdf = self._is_pdf(file_url, content)
            
            if is_pdf:
                logger.info("Archivo detectado como PDF, procesando página por página")
                # Procesar PDF convirtiendo cada página a imagen
                text_result = self._process_pdf_with_gcp_vision(content)
            else:
                # Procesar como imagen
                text_result = self._process_with_gcp_vision(content)
            
            # Calcular costo (aproximado para Google Cloud Vision)
            cost = self._calculate_gcp_ocr_cost(len(text_result))
            
            return text_result, cost
            
        except requests.RequestException as e:
            logger.error(f"Error al descargar archivo desde {file_url}: {e}")
            raise ValueError(f"Error al descargar el archivo: {str(e)}")
        except Exception as e:
            logger.error(f"Error inesperado en GCP OCR: {e}")
            raise ValueError(f"Error inesperado: {str(e)}")
    
    def _is_pdf(self, file_url: str, content: bytes) -> bool:
        """Detecta si el archivo es un PDF por extensión o primeros bytes"""
        # Verificar por extensión en la URL
        path = urlparse(file_url).path.lower()
        if path.endswith(".pdf"):
            return True
        
        # Verificar por primeros bytes (PDF comienza con %PDF)
        if len(content) >= 4 and content[:4] == b'%PDF':
            return True
        
        return False
    
    def _process_pdf_with_gcp_vision(self, pdf_bytes: bytes) -> str:
        """Procesa un PDF convirtiendo cada página a imagen y aplicando OCR en paralelo"""
        if fitz is None:
            raise ValueError("PyMuPDF (fitz) no está instalado y es requerido para procesar PDFs")
        
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        try:
            with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
                total_pages = len(doc)
                logger.info(f"Procesando PDF con {total_pages} página(s) en paralelo")
                
                # DPI reducido para mejor rendimiento (150 en lugar de 200)
                dpi = int(os.getenv("PDF_OCR_DPI", "150"))
                
                # Convertir todas las páginas a imágenes ANTES de paralelizar
                # (las páginas de fitz no se pueden pasar directamente a threads)
                page_images = []
                for page_num, page in enumerate(doc, start=1):
                    logger.info(f"Convirtiendo página {page_num}/{total_pages} a imagen")
                    pix = page.get_pixmap(dpi=dpi)
                    img_bytes = pix.tobytes("png")
                    page_images.append((page_num, img_bytes))
                
                def process_page_image(page_data):
                    """Procesa una imagen de página individual"""
                    page_num, img_bytes = page_data
                    try:
                        logger.info(f"Procesando OCR de página {page_num}/{total_pages}")
                        
                        # Procesar la imagen con GCP Vision
                        page_text = self._process_image_bytes_with_gcp_vision(img_bytes)
                        
                        logger.info(f"Página {page_num} procesada: {len(page_text)} caracteres extraídos")
                        return page_num, page_text
                    except Exception as e:
                        logger.error(f"Error al procesar página {page_num}: {e}")
                        return page_num, ""
                
                # Procesar todas las imágenes en paralelo
                text_pages_dict = {}
                with ThreadPoolExecutor(max_workers=min(total_pages, 4)) as executor:
                    # Preparar todas las tareas
                    future_to_page = {
                        executor.submit(process_page_image, page_data): page_data[0]
                        for page_data in page_images
                    }
                    
                    # Recolectar resultados conforme se completan
                    for future in as_completed(future_to_page):
                        page_num, page_text = future.result()
                        text_pages_dict[page_num] = page_text
                
                # Ordenar páginas por número y combinar texto
                text_pages = [text_pages_dict[i] for i in sorted(text_pages_dict.keys())]
        
        except Exception as e:
            logger.error(f"Error al procesar PDF: {e}")
            raise ValueError(f"Error al procesar PDF: {str(e)}")
        
        full_text = "\n".join(text_pages)
        logger.info(f"PDF procesado completamente: {len(full_text)} caracteres totales")
        return full_text
    
    def _process_image_bytes_with_gcp_vision(self, image_bytes: bytes) -> str:
        """Procesa bytes de imagen con Google Cloud Vision API"""
        try:
            # Validar tamaño del contenido (GCP Vision tiene límites)
            max_size = 20 * 1024 * 1024  # 20MB
            if len(image_bytes) > max_size:
                raise ValueError(f"La imagen es demasiado grande: {len(image_bytes)} bytes (máximo: {max_size} bytes)")
            
            # Crear imagen para Vision API
            image = vision.Image(content=image_bytes)
            
            # Realizar detección de texto
            response = self.client.text_detection(image=image)
            
            if response.error.message:
                raise ValueError(f"Error de Google Cloud Vision: {response.error.message}")
            
            # Extraer texto de las anotaciones
            texts = response.text_annotations
            if not texts:
                logger.warning("No se detectó texto en la imagen")
                return ""
            
            # El primer elemento contiene todo el texto detectado
            full_text = texts[0].description
            return full_text
            
        except Exception as e:
            logger.error(f"Error al procesar imagen con GCP Vision: {e}")
            raise ValueError(f"Error al procesar con Google Cloud Vision: {str(e)}")
    
    def _process_with_gcp_vision(self, content: bytes) -> str:
        """Procesa el contenido con Google Cloud Vision API (para imágenes)"""
        
        try:
            # Validar que el contenido no esté vacío
            if not content:
                raise ValueError("El contenido del archivo está vacío")
            
            # Validar que el contenido sea una imagen válida
            try:
                from PIL import Image
                import io
                
                # Verificar que el contenido no esté vacío
                if len(content) < 100:  # Mínimo 100 bytes para una imagen válida
                    raise ValueError(f"El archivo es demasiado pequeño: {len(content)} bytes")
                
                # Verificar los primeros bytes para detectar el tipo de archivo
                content_start = content[:10]
                logger.info(f"Primeros bytes del archivo: {content_start}")
                
                # Intentar abrir la imagen para validar que sea válida
                image_pil = Image.open(io.BytesIO(content))
                
                # Obtener información de la imagen antes de verify()
                logger.info(f"Imagen detectada: formato={image_pil.format}, tamaño={image_pil.size}, modo={image_pil.mode}")
                
                # Verificar que la imagen no esté corrupta
                image_pil.verify()
                
                # Reabrir la imagen después de verify() (verify() cierra el archivo)
                image_pil = Image.open(io.BytesIO(content))
                
                logger.info(f"Imagen válida: {image_pil.format}, {image_pil.size}, {image_pil.mode}")
                
            except Exception as img_error:
                logger.error(f"El archivo no es una imagen válida: {img_error}")
                logger.error(f"Tamaño del contenido: {len(content)} bytes")
                logger.error(f"Primeros 50 bytes: {content[:50]}")
                raise ValueError(f"El archivo no es una imagen válida: {str(img_error)}")
            
            # Procesar usando el método de bytes de imagen
            text_result = self._process_image_bytes_with_gcp_vision(content)
            
            logger.info(f"Texto extraído exitosamente: {len(text_result)} caracteres")
            return text_result
            
        except Exception as e:
            logger.error(f"Error al procesar con GCP Vision: {e}")
            raise ValueError(f"Error al procesar con Google Cloud Vision: {str(e)}")
    
    def _validate_url(self, file_url: str) -> bool:
        """Valida que la URL sea accesible y contenga contenido válido"""
        try:
            # Verificar que sea una URL válida
            parsed = urlparse(file_url)
            if not parsed.scheme or not parsed.netloc:
                logger.error(f"URL inválida: {file_url}")
                return False
            
            # Si es URL de GCS, no validar con HEAD (puede dar 403 pero el archivo existe)
            if file_url.startswith("https://storage.googleapis.com/"):
                # Validar formato de URL
                url_parts = file_url.replace("https://storage.googleapis.com/", "").split("/", 1)
                return len(url_parts) == 2
            
            # Verificar que sea accesible y obtener información del contenido
            response = requests.head(file_url, timeout=10, allow_redirects=True)
            if response.status_code != 200:
                logger.error(f"URL no accesible: {file_url} (status: {response.status_code})")
                logger.error(f"Response headers: {dict(response.headers)}")
                return False
            
            # Verificar Content-Type
            content_type = response.headers.get('content-type', '').lower()
            logger.info(f"Content-Type detectado: {content_type}")
            
            # Verificar que sea un tipo de archivo soportado
            supported_types = ['image/', 'application/pdf', 'application/octet-stream']
            if not any(content_type.startswith(t) for t in supported_types):
                logger.warning(f"Tipo de contenido no soportado: {content_type}")
                # No rechazar automáticamente, algunos servidores no envían el Content-Type correcto
            
            # Verificar Content-Length
            content_length = response.headers.get('content-length')
            if content_length:
                size_mb = int(content_length) / (1024 * 1024)
                logger.info(f"Tamaño del archivo: {size_mb:.2f} MB")
                
                # Verificar que no sea demasiado grande
                if int(content_length) > 20 * 1024 * 1024:  # 20MB
                    logger.error(f"Archivo demasiado grande: {size_mb:.2f} MB")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error al validar URL {file_url}: {e}")
            return False
    
    def _calculate_gcp_ocr_cost(self, text_length: int) -> float:
        """
        Calcula el costo aproximado del OCR usando Google Cloud Vision
        Basado en los precios de Google Cloud Vision API
        """
        # Precio aproximado: $1.50 por 1,000 imágenes
        # Asumimos que cada documento es una imagen
        base_cost = 0.0015  # $1.50 / 1000
        
        # Costo adicional por caracteres (muy pequeño)
        char_cost = (text_length / 1000000) * 0.01  # $0.01 por 1M caracteres
        
        return base_cost + char_cost
    
    def _convert_google_drive_url(self, file_url: str) -> str:
        """Convierte enlace de Google Drive a enlace directo de descarga"""
        if "drive.google.com" in file_url:
            # Extraer ID del archivo
            if "/file/d/" in file_url:
                file_id = file_url.split("/file/d/")[1].split("/")[0]
                return f"https://drive.google.com/uc?export=download&id={file_id}"
        return file_url


class FallbackOCRService:
    """Servicio de OCR con fallback automático entre proveedores"""
    
    def __init__(self):
        self.services = []
        self._initialize_services()
    
    def _initialize_services(self):
        """Inicializa los servicios en orden de preferencia"""
        provider = (os.getenv("OCR_PROVIDER") or "").strip().lower()
        
        if provider == "mock":
            self.services = [MockOCRService()]
        elif provider == "local":
            self.services = [LocalOCRService(), MockOCRService()]
        elif provider == "azure":
            self.services = [OCRService(), LocalOCRService(), MockOCRService()]
        elif provider == "gcp":
            self.services = [GCPOCRService(), LocalOCRService(), MockOCRService()]
        else:
            # Autodetección por defecto
            self.services = []
            try:
                self.services.append(OCRService())
            except Exception:
                pass
            try:
                self.services.append(GCPOCRService())
            except Exception:
                pass
            try:
                self.services.append(LocalOCRService())
            except Exception:
                pass
            self.services.append(MockOCRService())
    
    def extract_text_from_url(self, file_url: str) -> Tuple[str, float]:
        """Extrae texto usando el primer servicio disponible"""
        last_error = None
        
        for i, service in enumerate(self.services):
            try:
                logger.info(f"Intentando OCR con servicio {i+1}/{len(self.services)}: {service.__class__.__name__}")
                text, cost = service.extract_text_from_url(file_url)
                logger.info(f"OCR exitoso con {service.__class__.__name__}")
                return text, cost
            except Exception as e:
                last_error = e
                logger.warning(f"Falló {service.__class__.__name__}: {e}")
                if i < len(self.services) - 1:
                    logger.info("Probando con el siguiente servicio...")
                continue
        
        # Si todos los servicios fallan
        logger.error("Todos los servicios de OCR fallaron")
        raise ValueError(f"Error en todos los servicios de OCR. Último error: {last_error}")


def get_ocr_service():
    """Factory para obtener el servicio de OCR según OCR_PROVIDER.

    OCR_PROVIDER:
      - "azure": usa Azure Computer Vision
      - "gcp": usa Google Cloud Vision API
      - "local": usa Tesseract (pytesseract) y PyMuPDF para PDF
      - "mock": usa texto simulado
      - "fallback": usa fallback automático entre servicios
    Por defecto: usa fallback automático.
    """

    provider = (os.getenv("OCR_PROVIDER") or "").strip().lower()

    if provider == "mock":
        return MockOCRService()
    if provider == "local":
        return LocalOCRService()
    if provider == "azure":
        return OCRService()
    if provider == "gcp":
        return GCPOCRService()
    if provider == "fallback":
        return FallbackOCRService()

    # Por defecto usar fallback
    return FallbackOCRService()
