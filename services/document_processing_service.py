"""
Servicio principal de procesamiento de documentos
Orquesta todas las capas de procesamiento
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from bson import ObjectId

from models.document_models import ProcessedDocument, ProcessingStatus, FinalDecision
from services.ai_services import DocumentAIService
from services.ocr_service import get_ocr_service
from database.mongodb_connection import get_collection
from utils.logging_utils import document_logging_context, set_stage
from services.capa_autenticidad import ejecutar_capa_autenticidad
from services.capa_ocr import ejecutar_capa_ocr
from services.capa_clasificacion import ejecutar_capa_clasificacion
from services.capa_validacion import ejecutar_capa_validacion

logger = logging.getLogger(__name__)


class DocumentProcessingService:
    """Servicio principal para el procesamiento de documentos"""
    
    def __init__(self):
        self.ai_service = DocumentAIService()
        self.ocr_service = get_ocr_service()
        # Inicializar colecciones de forma lazy para evitar errores al importar
        self._document_types_collection = None
        self._processed_documents_collection = None
    
    @property
    def document_types_collection(self):
        """Obtiene la colección de tipos de documentos (lazy)"""
        if self._document_types_collection is None:
            self._document_types_collection = get_collection("OCR_document_types")
        return self._document_types_collection
    
    @property
    def processed_documents_collection(self):
        """Obtiene la colección de documentos procesados (lazy)"""
        if self._processed_documents_collection is None:
            self._processed_documents_collection = get_collection("OCR_processed_documents")
        return self._processed_documents_collection
    
    def process_document(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Procesa un documento completo siguiendo el pipeline de capas
        
        Args:
            document_data: Datos del documento a procesar
            
        Returns:
            Dict con el resultado del procesamiento
        """
        
        document_id = document_data["document_id"]
        provided_classification = document_data.get("provided_classification")

        with document_logging_context(
            doc_id=document_id,
            provided_classification=provided_classification,
            stage="initialization",
        ):
            # Crear registro inicial del documento
            set_stage("create_record")
            processed_doc = self._create_processed_document(document_data)
            
            try:
                # Ejecutar pipeline de procesamiento
                set_stage("pipeline")
                result = self._execute_processing_pipeline(processed_doc)
                
                # Actualizar documento con resultado final
                set_stage("update_record")
                self._update_processed_document(processed_doc["_id"], result)
                set_stage("completed")
                
                return result
                
            except Exception as e:
                set_stage("error")
                logger.error(f"Error en procesamiento del documento {document_id}: {e}")
                # Marcar como fallido
                self._mark_document_as_failed(processed_doc["_id"], str(e))
                raise
    
    def _create_processed_document(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """Crea el registro inicial del documento procesado"""
        
        processed_doc = {
            "document_id": document_data["document_id"],
            "file_url": document_data["file_url"],
            "file_name": document_data.get("file_name", "document.pdf"),
            #"owner_user_name": document_data.get("owner_user_name"),
            "origin": document_data["origin"],
            "destination": document_data["destination"],
            "provided_classification": document_data["provided_classification"],
            "user_data": document_data.get("user_data"),
            "processing_status": ProcessingStatus.PENDING,
            "response_url": document_data.get("response_url"),
            "processing_cost_usd": 0.0,
            "processing_log": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Insertar en la base de datos
        result = self.processed_documents_collection.insert_one(processed_doc)
        processed_doc["_id"] = result.inserted_id
        
        logger.info(f"Documento {document_data['document_id']} creado con ID {result.inserted_id}")
        return processed_doc
    
    def _execute_processing_pipeline(self, processed_doc: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecuta el pipeline completo de procesamiento"""
        
        document_id = processed_doc["document_id"]
        context = {
            "processed_doc": processed_doc,
            "processing_log": [],
            "total_cost": 0.0,
            "rejection_reasons": [],
            "validation_results": []
        }
        
        try:
            # Capa 1: OCR
            logger.info(f"Iniciando OCR para documento {document_id}")
            context = ejecutar_capa_ocr(
                context=context,
                ocr_service=self.ocr_service,
                update_processing_status=self._update_processing_status,
            )
            
            # Capa 2: Verificación de Clasificación y Extracción
            logger.info(f"Iniciando verificación de clasificación para documento {document_id}")
            context = ejecutar_capa_clasificacion(
                context=context,
                document_types_collection=self.document_types_collection,
                ai_service=self.ai_service,
                update_processing_status=self._update_processing_status,
            )

            # Si la clasificación rechazó el documento, saltar autenticidad para evitar ruido
            if context.get("final_decision") == FinalDecision.REJECTED:
                logger.info(
                    "Documento rechazado durante clasificación; se omite verificación de autenticidad posterior."
                )
            else:
                logger.info(f"Evaluando necesidad de autenticidad para documento {document_id}")
                context = ejecutar_capa_autenticidad(context)
            
            # Capa 3: Validación de Reglas de Negocio
            if context.get("document_type_config"):
                logger.info(f"Iniciando validación de reglas para documento {document_id}")
                context = ejecutar_capa_validacion(
                    context=context,
                    ai_service=self.ai_service,
                    update_processing_status=self._update_processing_status,
                )
            else:
                logger.warning(f"No hay configuración de tipo de documento para {document_id}")
                context["final_decision"] = FinalDecision.MANUAL_REVIEW
                context["processing_log"].append("No se encontró configuración de tipo de documento")
            
            # Determinar decisión final
            context = self._determine_final_decision(context)
            
            return context
            
        except Exception as e:
            logger.error(f"Error en pipeline para documento {document_id}: {e}")
            context["final_decision"] = FinalDecision.MANUAL_REVIEW
            context["processing_log"].append(f"Error en pipeline: {str(e)}")
            raise
    
    
    def _determine_final_decision(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Determina la decisión final basada en los resultados"""
        
        set_stage("final_decision")
        
        if context.get("final_decision"):
            return context
        
        # Si hay razones de rechazo, rechazar
        if context.get("rejection_reasons"):
            context["final_decision"] = FinalDecision.REJECTED
            context["processing_log"].append("Documento rechazado por validaciones fallidas")
        else:
            context["final_decision"] = FinalDecision.APPROVED
            context["processing_log"].append("Documento aprobado")
        
        return context
    
    def _update_processing_status(self, document_id: ObjectId, status: ProcessingStatus):
        """Actualiza el estado de procesamiento del documento"""
        
        self.processed_documents_collection.update_one(
            {"_id": document_id},
            {
                "$set": {
                    "processing_status": status,
                    "updated_at": datetime.utcnow()
                }
            }
        )
    
    def _update_processed_document(self, document_id: ObjectId, result: Dict[str, Any]):
        """Actualiza el documento con el resultado final"""
        
        update_data = {
            "processing_status": ProcessingStatus.COMPLETED,
            "final_decision": result.get("final_decision"),
            "ocr_text": result.get("ocr_text"),
            "extracted_data": result.get("extracted_data"),
            "classification_result": result.get("classification_result"),
            "validation_results": result.get("validation_results"),
            "rejection_reasons": result.get("rejection_reasons"),
            "processing_cost_usd": result.get("total_cost", 0.0),
            "processing_log": result.get("processing_log", []),
            "document_type_id": result.get("document_type_id"),
            "document_type_name": result.get("document_type_name"),
            "processed_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        self.processed_documents_collection.update_one(
            {"_id": document_id},
            {"$set": update_data}
        )
    
    def _mark_document_as_failed(self, document_id: ObjectId, error_message: str):
        """Marca el documento como fallido"""
        
        set_stage("failed")
        
        self.processed_documents_collection.update_one(
            {"_id": document_id},
            {
                "$set": {
                    "processing_status": ProcessingStatus.FAILED,
                    "final_decision": FinalDecision.REJECTED,
                    "rejection_reasons": [{"reason": "Error de procesamiento", "details": error_message}],
                    "processing_log": [f"Error: {error_message}"],
                    "updated_at": datetime.utcnow()
                }
            }
        )
