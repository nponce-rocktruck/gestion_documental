"""
Procesador específico para Certificado F30 - Antecedentes Laborales y Previsionales
"""

import logging
import os
import json
from typing import Dict, Any, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from .base_processor import BaseDocumentProcessor
from services.verificacion_dt.vm_verification_client import VMVerificationClient
from services.storage_service import StorageService
from database.mongodb_connection import get_collection
from models.document_models import FinalDecision

logger = logging.getLogger(__name__)


class CertificadoF30Processor(BaseDocumentProcessor):
    """Procesador para Certificado F30 (Razón Social y Persona Natural)"""
    
    def __init__(self):
        # El nombre del tipo de documento se determinará dinámicamente según tipo_f30
        super().__init__(
            document_type_name="",  # Se establecerá dinámicamente
            requires_authenticity=True  # Solo F30 requiere autenticidad
        )
        self.tipo_f30 = None
    
    def process_document(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Procesa un documento F30 completo siguiendo el pipeline de capas.
        Selecciona el tipo de documento correcto según tipo_f30.
        
        Args:
            document_data: Datos del documento a procesar, debe incluir 'tipo_f30'
            
        Returns:
            Dict con el resultado del procesamiento
        """
        
        # Determinar el nombre del tipo de documento según tipo_f30
        self.tipo_f30 = document_data.get("tipo_f30", "razon_social")
        
        if self.tipo_f30 == "persona_natural":
            self.document_type_name = "Certificado F30 - Antecedentes Laborales y Previsionales - Persona Natural"
        else:  # razon_social (default)
            self.document_type_name = "Certificado F30 - Antecedentes Laborales y Previsionales - Razón Social"
        
        logger.info(f"Procesando F30 tipo: {self.tipo_f30} ({self.document_type_name})")
        
        # Llamar al método padre con el nombre correcto
        return super().process_document(document_data)
    
    def _execute_processing_pipeline(self, processed_doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta el pipeline completo de procesamiento con descarga automática
        """
        # Ejecutar pipeline base
        context = super()._execute_processing_pipeline(processed_doc)
        
        # Si pasó la autenticidad, ejecutar descarga automática
        if self.requires_authenticity and context.get("authenticity_result") == "PASSED":
            if context.get("final_decision") != FinalDecision.REJECTED:
                logger.info("Documento pasó autenticidad, iniciando descarga automática...")
                context = self._ejecutar_descarga_automatica(context)
        
        return context
    
    def _ejecutar_descarga_automatica(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta la descarga automática del documento original según el tipo de F30
        """
        document_id = context["processed_doc"]["document_id"]
        extracted_data = context.get("extracted_data", {})
        
        # Inicializar objeto de información de descarga
        download_info = {
            "download_status": "pending",
            "upload_status": "pending",
            "portal_url": None,
            "downloaded_file_path": None,
            "downloaded_file_name": None,
            "cloud_url": None,
            "cloud_bucket_path": None,
            "portal_message": None,
            "download_error": None,
            "upload_error": None,
            "extracted_data_downloaded": None,
            "downloaded_at": None,
            "uploaded_at": None
        }
        
        try:
            logger.info(f"Iniciando descarga automática para documento {document_id} (tipo: {self.tipo_f30})")
            
            if self.tipo_f30 == "persona_natural":
                # Descarga para persona natural
                result = self._descargar_persona_natural(extracted_data, document_id)
            else:
                # Descarga para razón social (usando código de certificado)
                result = self._descargar_razon_social(extracted_data, document_id)
            
            # Actualizar información de descarga
            download_info["download_status"] = "completed" if result.get("success") else "failed"
            download_info["portal_message"] = result.get("portal_message")
            download_info["download_error"] = result.get("error")
            download_info["downloaded_at"] = datetime.utcnow()
            
            # Si se descargó el archivo, subirlo a la nube y extraer datos
            if result.get("downloaded_file") and os.path.exists(result.get("downloaded_file")):
                downloaded_file_path = result.get("downloaded_file")
                download_info["downloaded_file_path"] = downloaded_file_path
                download_info["downloaded_file_name"] = os.path.basename(downloaded_file_path)
                
                # Subir a la nube
                logger.info(f"Subiendo archivo descargado a la nube: {downloaded_file_path}")
                storage_service = StorageService()
                upload_result = storage_service.upload_file_to_bucket(downloaded_file_path)
                
                if upload_result.get("success"):
                    download_info["upload_status"] = "completed"
                    download_info["cloud_url"] = upload_result.get("public_url")
                    download_info["cloud_bucket_path"] = upload_result.get("bucket_path")
                    download_info["uploaded_at"] = datetime.utcnow()
                    logger.info(f"Archivo subido exitosamente a la nube: {upload_result.get('public_url')}")
                    
                    # Eliminar archivo local después de subirlo exitosamente a la nube
                    try:
                        if os.path.exists(downloaded_file_path):
                            os.remove(downloaded_file_path)
                            logger.info(f"Archivo local eliminado exitosamente: {downloaded_file_path}")
                        else:
                            logger.warning(f"Archivo local no encontrado para eliminar: {downloaded_file_path}")
                    except Exception as e:
                        logger.error(f"Error al eliminar archivo local {downloaded_file_path}: {e}", exc_info=True)
                        # No fallar el proceso si no se puede eliminar el archivo local
                    
                    # Extraer datos del documento descargado usando la URL de la nube
                    cloud_url = upload_result.get("public_url")
                    logger.info(f"Extrayendo datos del documento descargado desde URL de la nube: {cloud_url}")
                    try:
                        extracted_data_downloaded = self._extraer_datos_documento_descargado(
                            cloud_url,
                            context
                        )
                        download_info["extracted_data_downloaded"] = extracted_data_downloaded
                        if extracted_data_downloaded:
                            logger.info("Datos extraídos exitosamente del documento descargado")
                            
                            # Comparar datos del documento enviado vs descargado
                            logger.info("Comparando datos del documento enviado con el descargado")
                            comparison_result = self._comparar_datos_documentos(
                                extracted_data,
                                extracted_data_downloaded,
                                context
                            )
                            download_info["data_comparison"] = comparison_result
                            
                            if not comparison_result.get("match", False):
                                # Hay diferencias significativas, rechazar documento
                                context["rejection_reasons"].append({
                                    "reason": "Diferencia entre documento enviado y descargado del portal oficial",
                                    "details": comparison_result.get("differences_summary", "Se encontraron diferencias entre los documentos"),
                                    "type": "data_mismatch",
                                    "differences": comparison_result.get("differences", [])
                                })
                                context["final_decision"] = FinalDecision.REJECTED
                                logger.warning(f"Documento rechazado por diferencias: {comparison_result.get('differences_summary')}")
                            else:
                                logger.info("Los datos del documento enviado coinciden con el descargado")
                        else:
                            logger.warning("No se pudieron extraer datos del documento descargado")
                    except Exception as e:
                        logger.error(f"Error al extraer datos del documento descargado: {e}", exc_info=True)
                        download_info["extracted_data_downloaded"] = None
                else:
                    download_info["upload_status"] = "failed"
                    download_info["upload_error"] = upload_result.get("error")
                    logger.error(f"Error al subir archivo a la nube: {upload_result.get('error')}")
                    download_info["extracted_data_downloaded"] = None
            
            # Guardar información completa en base de datos (incluye comparación si existe)
            self._guardar_informacion_descarga(document_id, download_info, result, context)
            
            # Agregar resultado al contexto
            context["download_automatic_result"] = result
            context["download_info"] = download_info
            context["processing_log"].append(
                f"Descarga automática: {result.get('message', 'Completada')}"
            )
            
            # Si hay error en la verificación (problema técnico), marcar para revisión manual
            if not result.get("success"):
                context["rejection_reasons"].append({
                    "reason": "Error en verificación automática - requiere revisión manual",
                    "details": result.get("error", "Error desconocido durante la verificación"),
                    "type": "verification_error",
                    "observacion": f"Error técnico durante la verificación: {result.get('error', 'Error desconocido')}. Se requiere revisión manual del documento."
                })
                context["final_decision"] = FinalDecision.MANUAL_REVIEW
                logger.warning(f"Error en verificación automática, marcado para revisión manual: {result.get('error')}")
            elif not result.get("valid"):
                # Certificado no válido (no es error técnico, es que el certificado realmente no es válido)
                context["rejection_reasons"].append({
                    "reason": "Certificado no válido en portal oficial",
                    "details": result.get("error_message", "Certificado no válido"),
                    "type": "invalid_certificate",
                    "folios_ingresados": result.get("folios_ingresados")
                })
                context["final_decision"] = FinalDecision.REJECTED
            
        except Exception as e:
            logger.error(f"Error en descarga automática para documento {document_id}: {e}", exc_info=True)
            context["processing_log"].append(f"Error en descarga automática: {str(e)}")
            download_info["download_status"] = "failed"
            download_info["download_error"] = str(e)
            context["download_automatic_result"] = {
                "success": False,
                "error": str(e)
            }
            context["download_info"] = download_info
            self._guardar_informacion_descarga(document_id, download_info, {"success": False, "error": str(e)}, context)
            
            # CRÍTICO: Si hay error en la descarga automática, cambiar a revisión manual
            # No debe quedar como APPROVED si falló un paso crítico
            if context.get("final_decision") == FinalDecision.APPROVED:
                context["rejection_reasons"].append({
                    "reason": "Error en descarga automática - requiere revisión manual",
                    "details": str(e),
                    "type": "download_error"
                })
                context["final_decision"] = FinalDecision.MANUAL_REVIEW
                logger.warning(f"Documento cambiado a MANUAL_REVIEW debido a error en descarga automática: {str(e)}")
        
        return context
    
    def _descargar_persona_natural(
        self, 
        extracted_data: Dict[str, Any], 
        document_id: str
    ) -> Dict[str, Any]:
        """Descarga certificado F30 para persona natural"""
        
        # Extraer datos necesarios
        folio_oficina = extracted_data.get("folio_oficina", "")
        folio_anio = extracted_data.get("folio_anio", "")
        folio_numero_consecutivo = extracted_data.get("folio_numero_consecutivo", "")
        codigo_verificacion = extracted_data.get("codigo_verificacion", "")
        
        if not all([folio_oficina, folio_anio, folio_numero_consecutivo, codigo_verificacion]):
            logger.error(f"Faltan datos para descarga persona natural: {extracted_data}")
            return {
                "success": False,
                "valid": False,
                "message": "Faltan datos necesarios para descarga",
                "error": "Datos incompletos en extracted_data",
                "folios_ingresados": {
                    "folio_oficina": folio_oficina,
                    "folio_anio": folio_anio,
                    "folio_numero_consecutivo": folio_numero_consecutivo,
                    "codigo_verificacion": codigo_verificacion
                }
            }
        
        logger.info(f"Descargando F30 persona natural: {folio_oficina}/{folio_anio}/{folio_numero_consecutivo} - {codigo_verificacion}")
        
        # Configurar directorio de descarga
        download_dir = os.getenv("F30_DOWNLOAD_DIR", "downloads/f30")
        os.makedirs(download_dir, exist_ok=True)
        
        # Usar cliente de VM para verificación
        try:
            client = VMVerificationClient()
            result = client.verificar_persona_natural(
                folio_oficina=folio_oficina,
                folio_anio=folio_anio,
                folio_numero=folio_numero_consecutivo,
                codigo_verificacion=codigo_verificacion,
                document_id=document_id,
                timeout=180
            )
            return result
        except Exception as e:
            logger.error(f"Error al ejecutar verificación en thread separado: {e}", exc_info=True)
            return {
                "success": False,
                "valid": False,
                "message": "Error durante la verificación",
                "error": str(e),
                "folios_ingresados": {
                    "folio_oficina": folio_oficina,
                    "folio_anio": folio_anio,
                    "folio_numero_consecutivo": folio_numero_consecutivo,
                    "codigo_verificacion": codigo_verificacion
                }
            }
    
    def _descargar_razon_social(
        self, 
        extracted_data: Dict[str, Any], 
        document_id: str
    ) -> Dict[str, Any]:
        """Descarga certificado F30 para razón social"""
        
        # Extraer código de certificado
        codigo_certificado = extracted_data.get("codigo_certificado", "")
        
        if not codigo_certificado:
            logger.error(f"Falta código de certificado para descarga razón social: {extracted_data}")
            return {
                "success": False,
                "valid": False,
                "message": "Falta código de certificado",
                "error": "Código de certificado no encontrado en extracted_data"
            }
        
        logger.info(f"Descargando F30 razón social con código: {codigo_certificado}")
        
        # Configurar directorio de descarga
        download_dir = os.getenv("F30_DOWNLOAD_DIR", "downloads/f30")
        os.makedirs(download_dir, exist_ok=True)
        
        # Formatear código (puede venir con o sin espacios)
        codigo_formateado = codigo_certificado.replace(" ", "").upper()
        # Agregar espacios cada 4 caracteres si no los tiene
        if " " not in codigo_certificado and len(codigo_formateado) >= 8:
            codigo_formateado = " ".join([codigo_formateado[i:i+4] for i in range(0, len(codigo_formateado), 4)])
        
        # Usar cliente de VM para verificación
        try:
            client = VMVerificationClient()
            result = client.verificar_portal_documental(
                codigo=codigo_formateado,
                document_id=document_id
            )
            return result
        except Exception as e:
            logger.error(f"Error al ejecutar verificación en thread separado: {e}", exc_info=True)
            return {
                "success": False,
                "valid": False,
                "message": "Error durante la verificación",
                "error": str(e)
            }
    
    def _guardar_informacion_descarga(
        self, 
        document_id: str, 
        download_info: Dict[str, Any],
        result: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ):
        """Guarda toda la información del proceso de descarga en la base de datos"""
        try:
            collection = get_collection("OCR_processed_documents")
            
            # Preparar objeto completo de información de descarga
            download_data = {
                "download_info": download_info,
                "download_automatic_result": result,
                "download_automatic_at": datetime.utcnow(),
                "tipo_f30": self.tipo_f30,
                "updated_at": datetime.utcnow()
            }
            
            # Guardar explícitamente los datos extraídos del documento descargado en un campo separado
            # para facilitar consultas y análisis posteriores
            if download_info.get("extracted_data_downloaded"):
                download_data["extracted_data_downloaded"] = download_info["extracted_data_downloaded"]
            
            # Guardar explícitamente el resultado de la comparación en un campo separado
            if download_info.get("data_comparison"):
                download_data["data_comparison"] = download_info["data_comparison"]
            
            # Guardar información de uso de proxy si está disponible
            if result.get("proxy_usage"):
                download_data["proxy_usage"] = result["proxy_usage"]
                download_data["proxy_usage_mb"] = result["proxy_usage"].get("estimated_mb", 0.0)
            
            collection.update_one(
                {"document_id": document_id},
                {
                    "$set": download_data,
                    "$push": {
                        "processing_log": {
                            "$each": [
                                f"[DESCARGA AUTOMÁTICA] Tipo: {self.tipo_f30} - {result.get('message', 'Completada')}",
                                f"[DESCARGA AUTOMÁTICA] Éxito: {result.get('success', False)}, Válido: {result.get('valid', False)}",
                                f"[DESCARGA AUTOMÁTICA] Status descarga: {download_info.get('download_status')}, Status upload: {download_info.get('upload_status')}"
                            ],
                            "$slice": -1000
                        }
                    }
                }
            )
            
            # Si hay folios ingresados, registrarlos también
            if result.get("folios_ingresados"):
                collection.update_one(
                    {"document_id": document_id},
                    {
                        "$set": {
                            "download_folios_ingresados": result.get("folios_ingresados")
                        }
                    }
                )
            
            # Si hay resultado de comparación de datos, agregarlo a los logs
            if download_info.get("data_comparison"):
                comparison = download_info["data_comparison"]
                comparison_logs = [
                    f"[COMPARACIÓN DE DATOS] Método: {comparison.get('comparison_method', 'unknown')}",
                    f"[COMPARACIÓN DE DATOS] Coinciden: {comparison.get('match', False)}",
                    f"[COMPARACIÓN DE DATOS] Resumen: {comparison.get('differences_summary', 'N/A')}"
                ]
                
                if comparison.get("differences"):
                    comparison_logs.append(
                        f"[COMPARACIÓN DE DATOS] Número de diferencias: {len(comparison['differences'])}"
                    )
                    # Agregar detalles de diferencias (limitado a primeros 5 para no saturar logs)
                    for i, diff in enumerate(comparison["differences"][:5]):
                        comparison_logs.append(
                            f"[COMPARACIÓN DE DATOS] Diferencia {i+1}: Campo '{diff.get('field')}' - "
                            f"Enviado: {str(diff.get('uploaded_value', 'N/A'))[:50]}, "
                            f"Descargado: {str(diff.get('downloaded_value', 'N/A'))[:50]}"
                        )
                
                collection.update_one(
                    {"document_id": document_id},
                    {
                        "$push": {
                            "processing_log": {
                                "$each": comparison_logs,
                                "$slice": -1000
                            }
                        }
                    }
                )
            
            logger.info(f"Información de descarga guardada para documento {document_id}")
        except Exception as e:
            logger.error(f"Error al guardar información de descarga: {e}", exc_info=True)
    
    def _extraer_datos_documento_descargado(
        self,
        file_url: str,
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Extrae datos del documento descargado del portal usando OCR y el schema de extracción
        
        Args:
            file_url: URL del archivo subido a la nube
            context: Contexto del procesamiento que contiene la configuración del tipo de documento
        
        Returns:
            Dict con los datos extraídos o None si hay error
        """
        try:
            # Obtener el tipo de documento configurado
            document_type_config = context.get("document_type_config")
            if not document_type_config:
                logger.warning("No hay configuración de tipo de documento para extraer datos del documento descargado")
                return None
            
            extraction_schema = document_type_config.get("extraction_schema")
            if not extraction_schema:
                logger.warning("No hay schema de extracción para el documento descargado")
                return None
            
            # Ejecutar OCR en el archivo desde la URL de la nube
            logger.info(f"Ejecutando OCR en documento descargado desde URL: {file_url}")
            ocr_text, ocr_cost = self.ocr_service.extract_text_from_url(file_url)
            
            if not ocr_text or len(ocr_text.strip()) == 0:
                logger.warning("No se pudo extraer texto del documento descargado")
                return None
            
            # Extraer datos usando el schema
            logger.info("Extrayendo datos del documento descargado usando schema")
            extracted_data, extraction_cost = self.ai_service.extract_data_with_schema(
                ocr_text,
                extraction_schema
            )
            
            # Actualizar costo total
            context["total_cost"] += ocr_cost + extraction_cost
            context["processing_log"].append(
                f"Extracción de datos del documento descargado completada. Costo OCR: ${ocr_cost:.6f}, Costo extracción: ${extraction_cost:.6f}"
            )
            
            logger.info("Datos extraídos exitosamente del documento descargado")
            return extracted_data
            
        except Exception as e:
            logger.error(f"Error al extraer datos del documento descargado: {e}", exc_info=True)
            return None
    
    def _comparar_datos_documentos(
        self,
        extracted_data_uploaded: Dict[str, Any],
        extracted_data_downloaded: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compara los datos extraídos del documento enviado con los del documento descargado.
        Usa comparación programática primero y luego IA para analizar diferencias significativas.
        
        Args:
            extracted_data_uploaded: Datos extraídos del documento enviado por el usuario
            extracted_data_downloaded: Datos extraídos del documento descargado del portal
            context: Contexto del procesamiento para logs y costos
        
        Returns:
            Dict con resultado de la comparación con la siguiente estructura:
            {
                "match": bool,  # True si los documentos son equivalentes, False si hay diferencias significativas
                "differences": [  # Lista de diferencias encontradas (campo por campo)
                    {
                        "field": str,  # Nombre del campo con diferencia
                        "uploaded_value": Any,  # Valor en el documento enviado
                        "downloaded_value": Any,  # Valor en el documento descargado
                        "normalized_uploaded": Any,  # Valor normalizado del documento enviado
                        "normalized_downloaded": Any  # Valor normalizado del documento descargado
                    },
                    ...
                ],
                "differences_summary": str,  # Resumen textual de las diferencias (generado por IA si aplica)
                "comparison_method": str,  # "programmatic" (solo comparación programática), "both" (programática + IA), o "error"
                "programmatic_result": {  # Resultado de la comparación programática
                    "match": bool,
                    "differences": [...],
                    "total_fields": int,
                    "matching_fields": int
                },
                "ai_analysis": {  # Solo presente si se usó IA (cuando comparison_method == "both")
                    "are_equivalent": bool,  # True si IA determinó que son equivalentes
                    "summary": str,  # Resumen del análisis de IA
                    "significant_differences": [str],  # Lista de campos con diferencias significativas
                    "format_differences": [str]  # Lista de campos con solo diferencias de formato
                }
            }
            
            Ejemplo de retorno cuando coinciden:
            {
                "match": True,
                "differences": [],
                "differences_summary": "Los datos coinciden perfectamente",
                "comparison_method": "programmatic",
                "programmatic_result": {...}
            }
            
            Ejemplo de retorno cuando hay diferencias pero no significativas:
            {
                "match": True,
                "differences": [{"field": "nombre", "uploaded_value": "Juan", "downloaded_value": "JUAN", ...}],
                "differences_summary": "Solo diferencias de formato (mayúsculas/minúsculas)",
                "comparison_method": "both",
                "programmatic_result": {...},
                "ai_analysis": {
                    "are_equivalent": True,
                    "summary": "Las diferencias son solo de formato...",
                    "significant_differences": [],
                    "format_differences": ["nombre"]
                }
            }
            
            Ejemplo de retorno cuando hay diferencias significativas:
            {
                "match": False,
                "differences": [{"field": "rut", "uploaded_value": "12345678-9", "downloaded_value": "98765432-1", ...}],
                "differences_summary": "Se encontraron diferencias en valores críticos como RUT",
                "comparison_method": "both",
                "programmatic_result": {...},
                "ai_analysis": {
                    "are_equivalent": False,
                    "summary": "Diferencias significativas en RUT y fecha de emisión",
                    "significant_differences": ["rut", "fecha_emision"],
                    "format_differences": []
                }
            }
        """
        try:
            logger.info("Iniciando comparación de datos entre documento enviado y descargado")
            context["processing_log"].append("Iniciando comparación de datos entre documentos")
            
            # Primero: comparación programática campo por campo
            programmatic_result = self._comparar_datos_programatico(
                extracted_data_uploaded,
                extracted_data_downloaded
            )
            
            # Si no hay diferencias en la comparación programática, retornar éxito
            if programmatic_result["match"]:
                logger.info("Los datos coinciden perfectamente (comparación programática)")
                context["processing_log"].append("Comparación programática: Los datos coinciden perfectamente")
                return {
                    "match": True,
                    "differences": [],
                    "differences_summary": "Los datos coinciden perfectamente",
                    "comparison_method": "programmatic",
                    "programmatic_result": programmatic_result
                }
            
            # Si hay diferencias, usar IA para determinar si son significativas
            logger.info(f"Se encontraron {len(programmatic_result['differences'])} diferencias. Analizando con IA si son significativas...")
            context["processing_log"].append(
                f"Comparación programática encontró {len(programmatic_result['differences'])} diferencias. "
                "Analizando con IA si son significativas..."
            )
            
            ai_result = self._analizar_diferencias_con_ia(
                extracted_data_uploaded,
                extracted_data_downloaded,
                programmatic_result["differences"],
                context
            )
            
            # Determinar resultado final basado en análisis de IA
            match = ai_result.get("are_equivalent", False)
            differences_summary = ai_result.get("summary", "Diferencias encontradas entre documentos")
            
            if match:
                logger.info(f"IA determinó que las diferencias no son significativas: {differences_summary}")
                context["processing_log"].append(
                    f"Análisis IA: Las diferencias no son significativas. {differences_summary}"
                )
            else:
                logger.warning(f"IA determinó que hay diferencias significativas: {differences_summary}")
                context["processing_log"].append(
                    f"Análisis IA: Se encontraron diferencias significativas. {differences_summary}"
                )
            
            return {
                "match": match,
                "differences": programmatic_result["differences"],
                "differences_summary": differences_summary,
                "comparison_method": "both",
                "programmatic_result": programmatic_result,
                "ai_analysis": ai_result
            }
            
        except Exception as e:
            logger.error(f"Error al comparar datos de documentos: {e}", exc_info=True)
            context["processing_log"].append(f"Error en comparación de datos: {str(e)}")
            # En caso de error, ser conservador y rechazar
            return {
                "match": False,
                "differences": [],
                "differences_summary": f"Error al comparar documentos: {str(e)}",
                "comparison_method": "error",
                "error": str(e)
            }
    
    def _comparar_datos_programatico(
        self,
        data1: Dict[str, Any],
        data2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compara dos diccionarios de datos campo por campo de forma programática.
        Normaliza valores para comparación (espacios, mayúsculas, etc.)
        
        Returns:
            Dict con match (bool) y differences (lista)
        """
        differences = []
        all_keys = set(data1.keys()) | set(data2.keys())
        
        for key in all_keys:
            val1 = data1.get(key)
            val2 = data2.get(key)
            
            # Normalizar valores para comparación
            normalized_val1 = self._normalizar_valor_comparacion(val1)
            normalized_val2 = self._normalizar_valor_comparacion(val2)
            
            if normalized_val1 != normalized_val2:
                differences.append({
                    "field": key,
                    "uploaded_value": val1,
                    "downloaded_value": val2,
                    "normalized_uploaded": normalized_val1,
                    "normalized_downloaded": normalized_val2
                })
        
        return {
            "match": len(differences) == 0,
            "differences": differences,
            "total_fields": len(all_keys),
            "matching_fields": len(all_keys) - len(differences)
        }
    
    def _normalizar_valor_comparacion(self, value: Any) -> Any:
        """
        Normaliza un valor para comparación (quita espacios, normaliza mayúsculas, etc.)
        """
        if value is None:
            return None
        
        if isinstance(value, str):
            # Quitar espacios extra, convertir a mayúsculas, quitar acentos básicos
            normalized = value.strip().upper()
            # Reemplazar múltiples espacios por uno solo
            normalized = " ".join(normalized.split())
            return normalized
        
        if isinstance(value, (int, float)):
            return value
        
        if isinstance(value, list):
            return [self._normalizar_valor_comparacion(item) for item in value]
        
        if isinstance(value, dict):
            return {k: self._normalizar_valor_comparacion(v) for k, v in value.items()}
        
        return value
    
    def _analizar_diferencias_con_ia(
        self,
        extracted_data_uploaded: Dict[str, Any],
        extracted_data_downloaded: Dict[str, Any],
        differences: list,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Usa IA para analizar si las diferencias encontradas son significativas o solo de formato.
        
        Returns:
            Dict con are_equivalent (bool) y summary (str)
        """
        try:
            import json
            
            # Preparar prompt para IA
            prompt = f"""Analiza las siguientes diferencias entre dos versiones del mismo documento F30 (una enviada por el usuario y otra descargada del portal oficial).

Datos del documento enviado:
{json.dumps(extracted_data_uploaded, indent=2, ensure_ascii=False, default=str)}

Datos del documento descargado:
{json.dumps(extracted_data_downloaded, indent=2, ensure_ascii=False, default=str)}

Diferencias encontradas:
{json.dumps(differences, indent=2, ensure_ascii=False, default=str)}

Determina si estas diferencias son:
1. Solo diferencias de formato (espacios, mayúsculas, puntuación, etc.) - NO significativas
2. Diferencias en valores reales (números, fechas, nombres, códigos diferentes) - SÍ significativas

Responde ÚNICAMENTE en formato JSON válido con esta estructura exacta:
{{
  "are_equivalent": true/false,
  "summary": "string breve explicando el análisis",
  "significant_differences": ["campo1", "campo2"],
  "format_differences": ["campo3", "campo4"]
}}

IMPORTANTE: 
- Si los valores son funcionalmente equivalentes (mismo contenido, diferente formato), marca are_equivalent como true
- Si hay diferencias en valores reales (números, fechas, nombres, códigos), marca are_equivalent como false
- Responde SOLO con el JSON, sin texto adicional"""

            # Llamar a IA para análisis usando el cliente directamente
            from openai import OpenAI
            import os
            
            api_key = os.getenv("AI_API_KEY")
            base_url = os.getenv("AI_BASE_URL", "https://api.openai.com/v1")
            model = os.getenv("AI_MODEL", "gpt-4o-mini")
            
            client = OpenAI(api_key=api_key, base_url=base_url)
            
            # Intentar con response_format primero (para modelos que lo soportan)
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "system",
                            "content": "Eres un experto analista de documentos. Analiza diferencias entre documentos y determina si son significativas o solo de formato. Responde SOLO en formato JSON válido."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,
                    max_tokens=2000,
                    response_format={"type": "json_object"}
                )
            except Exception as e:
                # Si falla, intentar sin response_format
                logger.warning(f"No se pudo usar response_format, intentando sin él: {e}")
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "system",
                            "content": "Eres un experto analista de documentos. Analiza diferencias entre documentos y determina si son significativas o solo de formato. Responde SOLO en formato JSON válido."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,
                    max_tokens=2000
                )
            
            result_text = response.choices[0].message.content.strip()
            analysis_cost = self._calculate_ai_cost(response.usage)
            context["total_cost"] += analysis_cost
            context["processing_log"].append(
                f"Análisis IA de diferencias completado. Costo: ${analysis_cost:.6f}"
            )
            
            # Parsear respuesta JSON (puede venir con markdown)
            try:
                # Limpiar la respuesta para extraer solo el JSON
                cleaned_text = result_text.strip()
                
                # Si la respuesta contiene markdown, extraer solo el JSON
                if "```json" in cleaned_text:
                    start = cleaned_text.find("```json") + 7
                    end = cleaned_text.find("```", start)
                    if end != -1:
                        cleaned_text = cleaned_text[start:end].strip()
                elif "```" in cleaned_text:
                    start = cleaned_text.find("```") + 3
                    end = cleaned_text.find("```", start)
                    if end != -1:
                        cleaned_text = cleaned_text[start:end].strip()
                
                # Buscar el primer { y último } para extraer JSON
                first_brace = cleaned_text.find("{")
                last_brace = cleaned_text.rfind("}")
                if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
                    cleaned_text = cleaned_text[first_brace:last_brace + 1]
                
                analysis_result = json.loads(cleaned_text)
                
                # Validar estructura
                if "are_equivalent" not in analysis_result:
                    analysis_result["are_equivalent"] = False
                if "summary" not in analysis_result:
                    analysis_result["summary"] = "Análisis completado"
                if "significant_differences" not in analysis_result:
                    analysis_result["significant_differences"] = []
                if "format_differences" not in analysis_result:
                    analysis_result["format_differences"] = []
                
                return analysis_result
            except json.JSONDecodeError as e:
                logger.error(f"Error al parsear respuesta JSON de análisis IA: {e}")
                logger.error(f"Respuesta recibida: {result_text[:500]}")
                # Fallback: ser conservador
                return {
                    "are_equivalent": False,
                    "summary": f"Error al procesar análisis IA: {str(e)}",
                    "significant_differences": [d["field"] for d in differences],
                    "format_differences": []
                }
            
        except Exception as e:
            logger.error(f"Error al analizar diferencias con IA: {e}", exc_info=True)
            # En caso de error, ser conservador
            return {
                "are_equivalent": False,
                "summary": f"Error al analizar diferencias: {str(e)}. Se asume que hay diferencias significativas.",
                "significant_differences": [d["field"] for d in differences],
                "format_differences": []
            }
    
    def _calculate_ai_cost(self, usage) -> float:
        """Calcula el costo de la llamada a la API de IA"""
        if not usage:
            return 0.0
        
        # Precios aproximados por 1K tokens (ajustar según el modelo)
        input_price_per_1k = 0.00015  # $0.15 por 1K tokens de entrada
        output_price_per_1k = 0.0006   # $0.60 por 1K tokens de salida
        
        input_tokens = usage.prompt_tokens
        output_tokens = usage.completion_tokens
        
        input_cost = (input_tokens / 1000) * input_price_per_1k
        output_cost = (output_tokens / 1000) * output_price_per_1k
        
        return input_cost + output_cost

