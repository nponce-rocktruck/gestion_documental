"""
Servicios de IA para la nueva API de Documentos
Basado en el DocumentIAClient del proyecto original pero adaptado para la nueva lógica
"""

import json
import os
from typing import Dict, Any, List, Tuple, Optional
from openai import OpenAI
import logging

logger = logging.getLogger(__name__)


class DocumentAIService:
    """Servicio de IA para procesamiento de documentos"""
    
    def __init__(self):
        # Configuración de IA (OpenAI/DeepSeek)
        self.api_key = os.getenv("AI_API_KEY")
        self.base_url = os.getenv("AI_BASE_URL", "https://api.openai.com/v1")
        self.model = os.getenv("AI_MODEL", "gpt-4o-mini")
        
        if not self.api_key:
            raise ValueError("AI_API_KEY no está configurada")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    def _calculate_cost(self, usage) -> float:
        """Calcula el costo de la llamada a la API"""
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
    
    def verify_document_classification(
        self, 
        ocr_text: str, 
        provided_classification: str,
        available_document_types: List[Dict[str, Any]]
    ) -> Tuple[Dict[str, Any], float]:
        """
        Verifica si la clasificación proporcionada por el usuario es correcta
        usando IA para analizar el documento.
        """
        
        # Preparar la lista de tipos de documentos disponibles
        # Convertir ObjectId a string para serialización JSON
        serializable_types = []
        for doc_type in available_document_types:
            doc_type_copy = doc_type.copy()
            if '_id' in doc_type_copy:
                doc_type_copy['_id'] = str(doc_type_copy['_id'])
            serializable_types.append(doc_type_copy)
        
        available_types_str = json.dumps(serializable_types, indent=2, ensure_ascii=False, default=str)
        
        # Truncar texto OCR para optimizar
        truncated_ocr = self._truncate_ocr_text(ocr_text)
        
        prompt = f"""
        **Rol y Objetivo:**
        Eres un experto analista de documentos. Tu tarea es verificar si la clasificación proporcionada por el usuario es correcta.

        **Datos de Entrada:**
        
        - **CLASIFICACIÓN PROPORCIONADA POR EL USUARIO:** {provided_classification}
        
        - **TIPOS DE DOCUMENTOS DISPONIBLES:**
        ```json
        {available_types_str}
        ```

        - **TEXTO DEL DOCUMENTO (OCR):**
        ---
        {truncated_ocr}
        ---

        **Instrucciones:**
        1. Analiza el contenido del documento OCR
        2. Compara con los tipos de documentos disponibles
        3. Determina si la clasificación proporcionada es correcta
        4. Si es correcta, devuelve el tipo de documento correspondiente
        5. Si no es correcta, indica el error

        **Formato de Salida OBLIGATORIO:**
        Devuelve únicamente un objeto JSON con esta estructura:

        ```json
        {{
            "is_correct": true/false,
            "document_type": "nombre_del_tipo_si_es_correcto",
            "confidence": 0.95,
            "reason": "explicación_del_resultado",
            "suggested_type": "tipo_sugerido_si_no_es_correcto"
        }}
        ```
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Eres un experto analista de documentos especializado en verificación de clasificaciones."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )
            
            result_text = response.choices[0].message.content.strip()
            cost = self._calculate_cost(response.usage)
            
            # Parsear la respuesta JSON
            try:
                # Limpiar la respuesta para extraer solo el JSON
                result_text = result_text.strip()
                
                # Si la respuesta contiene markdown, extraer solo el JSON
                if "```json" in result_text:
                    start = result_text.find("```json") + 7
                    end = result_text.find("```", start)
                    if end != -1:
                        result_text = result_text[start:end].strip()
                elif "```" in result_text:
                    start = result_text.find("```") + 3
                    end = result_text.find("```", start)
                    if end != -1:
                        result_text = result_text[start:end].strip()
                
                # Intentar parsear el JSON
                result = json.loads(result_text)
                
                # Validar que tenga los campos requeridos
                required_fields = ["is_correct", "confidence", "reason"]
                for field in required_fields:
                    if field not in result:
                        logger.warning(f"Campo requerido '{field}' no encontrado en respuesta de IA")
                        result[field] = None if field != "is_correct" else False
                
                return result, cost
                
            except json.JSONDecodeError as e:
                logger.error(f"Error al parsear respuesta JSON: {e}")
                logger.error(f"Respuesta recibida: {result_text[:500]}...")
                
                # Intentar extraer información básica de la respuesta
                is_correct = "true" in result_text.lower() or "correcto" in result_text.lower()
                confidence = 0.0
                if "confidence" in result_text.lower():
                    try:
                        import re
                        conf_match = re.search(r'confidence["\']?\s*:\s*([0-9.]+)', result_text, re.IGNORECASE)
                        if conf_match:
                            confidence = float(conf_match.group(1))
                    except:
                        pass
                
                return {
                    "is_correct": is_correct,
                    "document_type": None,
                    "confidence": confidence,
                    "reason": f"Error al procesar respuesta de IA: {str(e)}",
                    "suggested_type": None
                }, cost
                
        except Exception as e:
            logger.error(f"Error en verificación de clasificación: {e}")
            return {
                "is_correct": False,
                "document_type": None,
                "confidence": 0.0,
                "reason": f"Error en procesamiento: {str(e)}",
                "suggested_type": None
            }, 0.0
    
    def extract_data_with_schema(
        self, 
        ocr_text: str, 
        extraction_schema: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], float]:
        """
        Extrae datos del documento usando un schema específico
        """
        
        schema_str = json.dumps(extraction_schema, indent=2, ensure_ascii=False, default=str)
        
        # Truncar texto OCR para optimizar
        truncated_ocr = self._truncate_ocr_text(ocr_text)
        
        prompt = f"""
        **Rol y Objetivo:**
        Eres un experto en extracción de datos de documentos. Extrae la información del documento siguiendo EXACTAMENTE el schema proporcionado.

        **Schema de Extracción:**
        ```json
        {schema_str}
        ```

        **Texto del Documento:**
        ---
        {truncated_ocr}
        ---

        **Instrucciones:**
        1. Extrae los datos siguiendo el schema exactamente
        2. Usa los tipos de datos especificados
        3. Si un campo no se encuentra, usa null
        4. Para fechas, usa el formato especificado
        5. Para booleanos, usa true/false

        **Formato de Salida:**
        Devuelve únicamente un objeto JSON con los datos extraídos siguiendo el schema.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Eres un experto en extracción de datos de documentos."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            result_text = response.choices[0].message.content.strip()
            cost = self._calculate_cost(response.usage)
            
            try:
                # Limpiar la respuesta para extraer solo el JSON
                result_text = result_text.strip()
                
                # Si la respuesta contiene markdown, extraer solo el JSON
                if "```json" in result_text:
                    start = result_text.find("```json") + 7
                    end = result_text.find("```", start)
                    if end != -1:
                        result_text = result_text[start:end].strip()
                elif "```" in result_text:
                    start = result_text.find("```") + 3
                    end = result_text.find("```", start)
                    if end != -1:
                        result_text = result_text[start:end].strip()
                
                result = json.loads(result_text)
                return result, cost
            except json.JSONDecodeError as e:
                logger.error(f"Error al parsear datos extraídos: {e}")
                logger.error(f"Respuesta recibida: {result_text[:500]}...")
                return {}, cost
                
        except Exception as e:
            logger.error(f"Error en extracción de datos: {e}")
            return {}, 0.0
    
    def validate_general_rules(
        self,
        document_data: Dict[str, Any],
        general_rules: List[Dict[str, Any]],
        document_type: str
    ) -> Tuple[Dict[str, Any], float]:
        """
        Valida los datos del documento contra las reglas generales (no requieren datos del usuario)
        """
        
        rules_str = json.dumps(general_rules, indent=2, ensure_ascii=False, default=str)
        document_data_str = json.dumps(document_data, indent=2, ensure_ascii=False, default=str)
        
        prompt = f"""
        **Rol y Objetivo:**
        Eres un experto en validación de documentos. Aplica las reglas generales para validar los datos del documento.

        **Datos del Documento:**
        ```json
        {document_data_str}
        ```

        **Reglas Generales:**
        ```json
        {rules_str}
        ```

        **Instrucciones:**
        1. Aplica cada regla general (no requieren datos del usuario)
        2. Para reglas de fecha, verifica las condiciones temporales
        3. Para reglas de formato, valida la estructura de los datos
        4. Para reglas de vigencia, verifica que el documento no esté vencido
        5. Evalúa cada regla independientemente

        **Formato de Salida:**
        Devuelve únicamente un objeto JSON con esta estructura:

        ```json
        {{
            "validaciones_detalladas": [
                {{
                    "nombre_regla": "nombre_de_la_regla",
                    "resultado": "APROBADO/RECHAZADO",
                    "razon": "explicación_del_resultado"
                }}
            ]
        }}
        ```
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Eres un experto en validación de reglas generales para documentos."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            result_text = response.choices[0].message.content.strip()
            cost = self._calculate_cost(response.usage)
            
            try:
                # Limpiar la respuesta para extraer solo el JSON
                result_text = result_text.strip()
                
                # Si la respuesta contiene markdown, extraer solo el JSON
                if "```json" in result_text:
                    start = result_text.find("```json") + 7
                    end = result_text.find("```", start)
                    if end != -1:
                        result_text = result_text[start:end].strip()
                elif "```" in result_text:
                    start = result_text.find("```") + 3
                    end = result_text.find("```", start)
                    if end != -1:
                        result_text = result_text[start:end].strip()
                
                result = json.loads(result_text)
                return result, cost
            except json.JSONDecodeError as e:
                logger.error(f"Error al parsear validaciones generales: {e}")
                logger.error(f"Respuesta recibida: {result_text[:500]}...")
                return {"validaciones_detalladas": []}, cost
                
        except Exception as e:
            logger.error(f"Error en validación de reglas generales: {e}")
            return {"validaciones_detalladas": []}, 0.0
    
    def validate_cross_validation_rules(
        self,
        document_data: Dict[str, Any],
        user_data: Dict[str, Any],
        validation_rules: List[Dict[str, Any]],
        document_type: str
    ) -> Tuple[Dict[str, Any], float]:
        """
        Valida los datos del documento contra los datos del usuario usando reglas de validación cruzada
        """
        
        rules_str = json.dumps(validation_rules, indent=2, ensure_ascii=False, default=str)
        document_data_str = json.dumps(document_data, indent=2, ensure_ascii=False, default=str)
        user_data_str = json.dumps(user_data, indent=2, ensure_ascii=False, default=str)
        
        prompt = f"""
        **Rol y Objetivo:**
        Eres un experto en validación cruzada de documentos. Compara los datos del documento con los datos del usuario.

        **Datos del Documento:**
        ```json
        {document_data_str}
        ```

        **Datos del Usuario:**
        ```json
        {user_data_str}
        ```

        **Reglas de Validación Cruzada:**
        ```json
        {rules_str}
        ```

        **Instrucciones:**
        1. Aplica cada regla de validación cruzada
        2. Para reglas de coincidencia, compara los campos correspondientes
        3. Para reglas parciales, usa coincidencias flexibles
        4. Para RUTs, normaliza y compara
        5. Para nombres, usa lógica flexible (coincidencias parciales)
        6. Evalúa cada regla independientemente

        **Formato de Salida:**
        Devuelve únicamente un objeto JSON con esta estructura:

        ```json
        {{
            "validaciones_detalladas": [
                {{
                    "nombre_regla": "nombre_de_la_regla",
                    "resultado": "APROBADO/RECHAZADO",
                    "razon": "explicación_del_resultado"
                }}
            ]
        }}
        ```
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Eres un experto en validación cruzada de documentos."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            result_text = response.choices[0].message.content.strip()
            cost = self._calculate_cost(response.usage)
            
            try:
                # Limpiar la respuesta para extraer solo el JSON
                result_text = result_text.strip()
                
                # Si la respuesta contiene markdown, extraer solo el JSON
                if "```json" in result_text:
                    start = result_text.find("```json") + 7
                    end = result_text.find("```", start)
                    if end != -1:
                        result_text = result_text[start:end].strip()
                elif "```" in result_text:
                    start = result_text.find("```") + 3
                    end = result_text.find("```", start)
                    if end != -1:
                        result_text = result_text[start:end].strip()
                
                result = json.loads(result_text)
                return result, cost
            except json.JSONDecodeError as e:
                logger.error(f"Error al parsear validaciones cruzadas: {e}")
                logger.error(f"Respuesta recibida: {result_text[:500]}...")
                return {"validaciones_detalladas": []}, cost
                
        except Exception as e:
            logger.error(f"Error en validación cruzada: {e}")
            return {"validaciones_detalladas": []}, 0.0
    
    def dynamic_user_data_validation(
        self,
        document_data: Dict[str, Any],
        user_data: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], float]:
        """
        Valida dinámicamente los datos del usuario contra los datos del documento
        """
        
        document_data_str = json.dumps(document_data, indent=2, ensure_ascii=False, default=str)
        user_data_str = json.dumps(user_data, indent=2, ensure_ascii=False, default=str)
        
        prompt = f"""
        **Rol y Objetivo:**
        Eres un experto en validación cruzada de datos. Compara los datos del usuario con los datos extraídos del documento.

        **Datos del Documento:**
        ```json
        {document_data_str}
        ```

        **Datos del Usuario:**
        ```json
        {user_data_str}
        ```

        **Instrucciones:**
        1. Compara cada campo del usuario con los campos correspondientes del documento
        2. Para coincidencias de nombres, usa lógica flexible (coincidencias parciales)
        3. Para RUTs, normaliza y compara
        4. Para fechas, verifica formatos y coherencia
        5. Si un campo del usuario no existe en el documento, alértalo
        6. Si los datos no coinciden, marca como error

        **Formato de Salida:**
        Devuelve únicamente un objeto JSON con esta estructura:

        ```json
        {{
            "validaciones_cruzadas": [
                {{
                    "campo_usuario": "nombre_del_campo",
                    "campo_documento": "nombre_del_campo_en_documento",
                    "coincide": true/false,
                    "valor_usuario": "valor_del_usuario",
                    "valor_documento": "valor_del_documento",
                    "tipo_validacion": "exacta/parcial/flexible",
                    "observaciones": "comentarios_adicionales"
                }}
            ],
            "campos_faltantes": ["lista_de_campos_del_usuario_que_no_estan_en_documento"],
            "resumen": {{
                "total_validaciones": 5,
                "coincidencias": 4,
                "errores": 1,
                "campos_faltantes": 0
            }}
        }}
        ```
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Eres un experto en validación cruzada de datos de documentos."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            result_text = response.choices[0].message.content.strip()
            cost = self._calculate_cost(response.usage)
            
            try:
                # Limpiar la respuesta para extraer solo el JSON
                result_text = result_text.strip()
                
                # Si la respuesta contiene markdown, extraer solo el JSON
                if "```json" in result_text:
                    start = result_text.find("```json") + 7
                    end = result_text.find("```", start)
                    if end != -1:
                        result_text = result_text[start:end].strip()
                elif "```" in result_text:
                    start = result_text.find("```") + 3
                    end = result_text.find("```", start)
                    if end != -1:
                        result_text = result_text[start:end].strip()
                
                result = json.loads(result_text)
                return result, cost
            except json.JSONDecodeError as e:
                logger.error(f"Error al parsear validación cruzada: {e}")
                logger.error(f"Respuesta recibida: {result_text[:500]}...")
                return {"validaciones_cruzadas": [], "campos_faltantes": [], "resumen": {}}, cost
                
        except Exception as e:
            logger.error(f"Error en validación cruzada: {e}")
            return {"validaciones_cruzadas": [], "campos_faltantes": [], "resumen": {}}, 0.0
    
    def _truncate_ocr_text(self, ocr_text: str, max_chars: int = 8000) -> str:
        """
        Trunca el texto OCR para reducir el tamaño de los prompts.
        Mantiene el inicio y el final del texto para preservar contexto.
        
        Args:
            ocr_text: Texto completo del OCR
            max_chars: Número máximo de caracteres a mantener
            
        Returns:
            Texto truncado
        """
        if len(ocr_text) <= max_chars:
            return ocr_text
        
        # Mantener inicio y final del texto
        chars_per_side = max_chars // 2
        truncated = ocr_text[:chars_per_side] + "\n\n[... texto intermedio omitido para optimización ...]\n\n" + ocr_text[-chars_per_side:]
        logger.info(f"Texto OCR truncado de {len(ocr_text)} a {len(truncated)} caracteres")
        return truncated
    
    def verify_and_extract_document(
        self,
        ocr_text: str,
        expected_document_type: str,
        document_type_config: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], float]:
        """
        Valida el tipo de documento Y extrae los datos en una sola llamada a la API.
        Optimización para reducir tiempo de procesamiento.
        
        Args:
            ocr_text: Texto extraído del documento por OCR
            expected_document_type: Nombre del tipo de documento esperado
            document_type_config: Configuración del tipo de documento desde la BD
            
        Returns:
            Tupla con (resultado combinado, costo)
            El resultado contiene tanto la validación como los datos extraídos
        """
        
        description = document_type_config.get("description", "")
        extraction_schema = document_type_config.get("extraction_schema", {})
        
        schema_str = json.dumps(extraction_schema, indent=2, ensure_ascii=False, default=str)
        
        # Truncar texto OCR para optimizar
        truncated_ocr = self._truncate_ocr_text(ocr_text)
        
        # Detectar si es un Certificado F30 para agregar instrucciones específicas
        is_f30_persona_natural = "Persona Natural" in expected_document_type and "F30" in expected_document_type
        is_f30_razon_social = "Razón Social" in expected_document_type and "F30" in expected_document_type
        
        # Instrucciones específicas para F30
        f30_instructions = ""
        if is_f30_persona_natural:
            f30_instructions = """
        
        **⚠️ REGLAS CRÍTICAS PARA CERTIFICADO F30 - PERSONA NATURAL:**
        
        La diferencia entre F30 Persona Natural y F30 Razón Social NO se basa en el nombre o razón social que aparece en el documento.
        
        **CRITERIOS DEFINITIVOS para validar F30 Persona Natural:**
        1. El documento DEBE tener un formato de FOLIO con estructura: "NÚMERO/AÑO/NÚMERO" (ej: "2000/2025/284236")
           - Esto indica: folio_oficina/folio_anio/folio_numero_consecutivo
        2. El documento DEBE tener un CÓDIGO DE VERIFICACIÓN alfanumérico al final del documento (ej: "L1n81y6G")
        3. El documento NO debe tener un código de certificado alfanumérico en la parte superior derecha (ese es para Razón Social)
        
        **IMPORTANTE - NO RECHAZAR POR ESTOS MOTIVOS:**
        - NO rechaces si el campo "RAZÓN SOCIAL / NOMBRE" contiene un nombre de empresa (ej: "TRANSFERVIÑACOSTA SPA")
        - NO rechaces si el RUT del solicitante es diferente al RUT del representante legal
        - Una persona natural puede tener un nombre de empresa y seguir siendo Persona Natural si tiene folios y código de verificación
        
        **VALIDACIÓN:**
        Si encuentras folio_oficina, folio_anio, folio_numero_consecutivo y codigo_verificacion → Es Persona Natural (APROBAR)
        Si encuentras codigo_certificado (código alfanumérico en parte superior derecha) → Es Razón Social (RECHAZAR)
        """
        elif is_f30_razon_social:
            f30_instructions = """
        
        **⚠️ REGLAS CRÍTICAS PARA CERTIFICADO F30 - RAZÓN SOCIAL:**
        
        **CRITERIOS DEFINITIVOS para validar F30 Razón Social:**
        1. El documento DEBE tener un CÓDIGO DE CERTIFICADO alfanumérico en la parte superior derecha (ej: "AVXYBVBONPLQ")
        2. El documento NO debe tener formato de FOLIO (NÚMERO/AÑO/NÚMERO)
        3. El documento NO debe tener código de verificación al final
        
        **VALIDACIÓN:**
        Si encuentras codigo_certificado (código alfanumérico en parte superior derecha) → Es Razón Social (APROBAR)
        Si encuentras folio_oficina, folio_anio, folio_numero_consecutivo y codigo_verificacion → Es Persona Natural (RECHAZAR)
        """
        
        prompt = f"""
        **Rol y Objetivo:**
        Eres un experto analista de documentos. Tu tarea es:
        1. Validar que el documento corresponde EXACTAMENTE al tipo esperado
        2. Si es válido, extraer los datos según el schema proporcionado

        **Tipo de Documento Esperado:**
        - **Nombre:** {expected_document_type}
        - **Descripción:** {description}
        {f30_instructions}
        **Schema de Extracción:**
        ```json
        {schema_str}
        ```

        **Texto del Documento (OCR):**
        ---
        {truncated_ocr}
        ---

        **Instrucciones:**
        1. Primero valida que el documento corresponde al tipo: "{expected_document_type}"
        2. Busca elementos característicos (marcas de agua, logos, campos específicos, estructura)
        3. Para F30: Usa EXCLUSIVAMENTE los criterios específicos mencionados arriba (folios/código_verificación vs código_certificado)
        4. Si el documento NO corresponde al tipo esperado, devuelve is_correct_type=false y NO extraigas datos
        5. Si el documento SÍ corresponde, extrae los datos siguiendo el schema exactamente

        **Formato de Salida OBLIGATORIO:**
        Devuelve únicamente un objeto JSON con esta estructura:

        ```json
        {{
            "is_correct_type": true/false,
            "confidence": 0.95,
            "reason": "explicación_del_resultado",
            "found_elements": ["lista_de_elementos_encontrados"],
            "extracted_data": {{...datos_extraídos_según_schema...}} o null si no es válido
        }}
        ```
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": f"Eres un experto analista de documentos. Validas tipos de documentos y extraes datos según schemas específicos."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=3000  # Más tokens para incluir datos extraídos
            )
            
            result_text = response.choices[0].message.content.strip()
            cost = self._calculate_cost(response.usage)
            
            # Parsear la respuesta JSON
            try:
                # Limpiar la respuesta para extraer solo el JSON
                result_text = result_text.strip()
                
                # Si la respuesta contiene markdown, extraer solo el JSON
                if "```json" in result_text:
                    start = result_text.find("```json") + 7
                    end = result_text.find("```", start)
                    if end != -1:
                        result_text = result_text[start:end].strip()
                elif "```" in result_text:
                    start = result_text.find("```") + 3
                    end = result_text.find("```", start)
                    if end != -1:
                        result_text = result_text[start:end].strip()
                
                # Intentar parsear el JSON
                result = json.loads(result_text)
                
                # Validar que tenga los campos requeridos
                if "is_correct_type" not in result:
                    result["is_correct_type"] = False
                if "extracted_data" not in result:
                    result["extracted_data"] = None if not result.get("is_correct_type") else {}
                
                return result, cost
                
            except json.JSONDecodeError as e:
                logger.error(f"Error al parsear respuesta JSON combinada: {e}")
                logger.error(f"Respuesta recibida: {result_text[:500]}...")
                
                # Fallback: intentar extraer información básica
                is_correct = "true" in result_text.lower() or "correcto" in result_text.lower()
                
                return {
                    "is_correct_type": is_correct,
                    "confidence": 0.0,
                    "reason": f"Error al procesar respuesta de IA: {str(e)}",
                    "found_elements": [],
                    "extracted_data": None if not is_correct else {}
                }, cost
                
        except Exception as e:
            logger.error(f"Error en validación y extracción combinada: {e}")
            return {
                "is_correct_type": False,
                "confidence": 0.0,
                "reason": f"Error en procesamiento: {str(e)}",
                "found_elements": [],
                "extracted_data": None
            }, 0.0
    
    def verify_document_type(
        self,
        ocr_text: str,
        expected_document_type: str,
        document_type_config: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], float]:
        """
        Valida que el documento corresponde al tipo específico esperado.
        No clasifica, solo valida que sea el tipo correcto.
        
        Args:
            ocr_text: Texto extraído del documento por OCR
            expected_document_type: Nombre del tipo de documento esperado
            document_type_config: Configuración del tipo de documento desde la BD
            
        Returns:
            Tupla con (resultado de validación, costo)
        """
        
        description = document_type_config.get("description", "")
        extraction_schema = document_type_config.get("extraction_schema", {})
        
        schema_str = json.dumps(extraction_schema, indent=2, ensure_ascii=False, default=str)
        
        # Truncar texto OCR para optimizar
        truncated_ocr = self._truncate_ocr_text(ocr_text)
        
        prompt = f"""
        **Rol y Objetivo:**
        Eres un experto analista de documentos. Tu tarea es validar que el documento proporcionado corresponde EXACTAMENTE al tipo de documento esperado.

        **Tipo de Documento Esperado:**
        - **Nombre:** {expected_document_type}
        - **Descripción:** {description}

        **Schema de Extracción Esperado:**
        ```json
        {schema_str}
        ```

        **Texto del Documento (OCR):**
        ---
        {truncated_ocr}
        ---

        **Instrucciones:**
        1. Analiza el contenido del documento OCR
        2. Verifica que el documento corresponde al tipo esperado: "{expected_document_type}"
        3. Busca elementos característicos del tipo de documento (marcas de agua, logos, campos específicos, estructura, etc.)
        4. Si el documento NO corresponde al tipo esperado, indica claramente por qué
        5. Si el documento SÍ corresponde, confirma la validación

        **Formato de Salida OBLIGATORIO:**
        Devuelve únicamente un objeto JSON con esta estructura:

        ```json
        {{
            "is_correct_type": true/false,
            "confidence": 0.95,
            "reason": "explicación_detallada_del_resultado",
            "found_elements": ["lista_de_elementos_característicos_encontrados"],
            "missing_elements": ["lista_de_elementos_característicos_no_encontrados"]
        }}
        ```
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": f"Eres un experto analista de documentos especializado en validar tipos específicos de documentos. Tu tarea es verificar que el documento corresponde exactamente al tipo: {expected_document_type}."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )
            
            result_text = response.choices[0].message.content.strip()
            cost = self._calculate_cost(response.usage)
            
            # Parsear la respuesta JSON
            try:
                # Limpiar la respuesta para extraer solo el JSON
                result_text = result_text.strip()
                
                # Si la respuesta contiene markdown, extraer solo el JSON
                if "```json" in result_text:
                    start = result_text.find("```json") + 7
                    end = result_text.find("```", start)
                    if end != -1:
                        result_text = result_text[start:end].strip()
                elif "```" in result_text:
                    start = result_text.find("```") + 3
                    end = result_text.find("```", start)
                    if end != -1:
                        result_text = result_text[start:end].strip()
                
                # Intentar parsear el JSON
                result = json.loads(result_text)
                
                # Validar que tenga los campos requeridos
                required_fields = ["is_correct_type", "confidence", "reason"]
                for field in required_fields:
                    if field not in result:
                        logger.warning(f"Campo requerido '{field}' no encontrado en respuesta de IA")
                        if field == "is_correct_type":
                            result[field] = False
                        else:
                            result[field] = None
                
                return result, cost
                
            except json.JSONDecodeError as e:
                logger.error(f"Error al parsear respuesta JSON: {e}")
                logger.error(f"Respuesta recibida: {result_text[:500]}...")
                
                # Intentar extraer información básica de la respuesta
                is_correct = "true" in result_text.lower() or "correcto" in result_text.lower() or "corresponde" in result_text.lower()
                confidence = 0.0
                if "confidence" in result_text.lower():
                    try:
                        import re
                        conf_match = re.search(r'confidence["\']?\s*:\s*([0-9.]+)', result_text, re.IGNORECASE)
                        if conf_match:
                            confidence = float(conf_match.group(1))
                    except:
                        pass
                
                return {
                    "is_correct_type": is_correct,
                    "confidence": confidence,
                    "reason": f"Error al procesar respuesta de IA: {str(e)}",
                    "found_elements": [],
                    "missing_elements": []
                }, cost
                
        except Exception as e:
            logger.error(f"Error en validación de tipo de documento: {e}")
            return {
                "is_correct_type": False,
                "confidence": 0.0,
                "reason": f"Error en procesamiento: {str(e)}",
                "found_elements": [],
                "missing_elements": []
            }, 0.0