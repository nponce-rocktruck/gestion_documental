# Documentación Técnica - API Certificado F30

## Descripción General

El servicio de Certificado F30 es una caja negra que procesa documentos de Antecedentes Laborales y Previsionales. El servicio acepta solicitudes de procesamiento y devuelve respuestas de forma asíncrona mediante callbacks.

**Versión API:** v1  
**Base Path:** `https://gestiondocumental-668060986147.us-central1.run.app/api/v1`  
**Tag:** `certificado-f30`

---

## Endpoint Principal

### POST `https://gestiondocumental-668060986147.us-central1.run.app/api/v1/certificado_f30`

Endpoint para procesar un Certificado F30 - Antecedentes Laborales y Previsionales.

**Características:**
- Procesamiento asíncrono (background)
- Solo acepta archivos PDF
- Requiere datos del usuario (`user_data`) para validación cruzada
- Soporta dos tipos de F30: `persona_natural` y `razon_social`

---

## Request

### Estructura del Request

```json
{
  "document_id": "string (requerido)",
  "file_url": "string (requerido, debe ser PDF)",
  "origin": "string (requerido)",
  "destination": "string (requerido)",
  "user_data": {
    // Ver sección "Estructura de user_data" para detalles según tipo_f30
  },
  "tipo_f30": "string (requerido: 'persona_natural' | 'razon_social')",
  "response_url": "string (opcional)"
}
```

### Campos del Request

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `document_id` | string | ✅ Sí | ID único del documento. Debe ser único en el sistema. |
| `file_url` | string | ✅ Sí | URL del archivo PDF a procesar. Debe terminar en `.pdf` |
| `origin` | string | ✅ Sí | Origen de la solicitud (identificador del sistema cliente) |
| `destination` | string | ✅ Sí | Destino de la respuesta (identificador del sistema destino) |
| `user_data` | object | ✅ Sí | Datos del usuario para validación cruzada. Ver sección "Estructura de user_data" para campos requeridos según `tipo_f30`. |
| `tipo_f30` | string | ✅ Sí | Tipo de certificado F30. Valores permitidos: `"persona_natural"` o `"razon_social"` |
| `response_url` | string | ❌ No | URL donde se enviará el resultado del procesamiento (callback). Si no se proporciona, el resultado solo estará disponible consultando el estado. |

### Estructura de `user_data`

El campo `user_data` debe contener los datos del usuario necesarios para validación cruzada. Los campos requeridos varían según el `tipo_f30`:

#### Para `tipo_f30: "razon_social"`

El `user_data` debe incluir los siguientes campos (el servicio buscará estos conceptos con diferentes nombres alternativos):

| Campo Requerido | Nombres Alternativos Aceptados | Tipo | Descripción |
|-----------------|-------------------------------|------|-------------|
| **RUT del Empleador** | `rut`, `run`, `tax_id` | string | RUT del empleador que debe coincidir con el RUT en el documento |
| **Razón Social** | `name`, `business_name`, `razon_social` | string | Razón social o nombre del empleador que debe coincidir con el documento |
| **Período a Validar** | `periodo_a_validar` | string/date | Período que se está validando (usado para validación de fecha de emisión) |

**Ejemplo para Razón Social:**
```json
{
  "user_data": {
    "rut": "12345678-9",
    "razon_social": "EMPRESA EJEMPLO S.A.",
    "periodo_a_validar": "2024-01"
  }
}
```

#### Para `tipo_f30: "persona_natural"`

El `user_data` debe incluir los siguientes campos (el servicio buscará estos conceptos con diferentes nombres alternativos):

| Campo Requerido | Nombres Alternativos Aceptados | Tipo | Descripción |
|-----------------|-------------------------------|------|-------------|
| **RUT de la Persona** | `rut`, `run`, `national_id` | string | RUT de la persona natural que debe coincidir con el RUT en el documento |
| **Nombre Completo** | `name`, `full_name` | string | Nombre completo de la persona que debe coincidir con el documento |
| **Período a Validar** | `periodo_a_validar` | string/date | Período que se está validando (usado para validación de fecha de emisión) |

**Ejemplo para Persona Natural:**
```json
{
  "user_data": {
    "rut": "12345678-9",
    "name": "Juan Pérez González",
    "periodo_a_validar": "2024-01"
  }
}
```

**Nota sobre nombres alternativos:** El servicio es flexible y acepta diferentes nombres de campos. Por ejemplo, para el RUT puede usar `rut`, `run`, `tax_id` (razón social) o `national_id` (persona natural). El servicio buscará automáticamente el campo correcto.

### Validaciones del Request

1. **Formato de archivo:** Solo se aceptan archivos PDF (extensión `.pdf`)
2. **Tipo F30:** Debe ser exactamente `"persona_natural"` o `"razon_social"`
3. **Documento único:** El `document_id` no puede estar siendo procesado actualmente
4. **URL válida:** El `file_url` debe ser una URL válida accesible
5. **user_data completo:** Debe incluir los campos requeridos según el `tipo_f30` (ver sección anterior)

### Ejemplos de Request

#### Ejemplo 1: Persona Natural

```json
{
  "document_id": "F30-2024-001",
  "file_url": "https://storage.example.com/documents/certificado_f30.pdf",
  "origin": "sistema-cliente-001",
  "destination": "sistema-destino-001",
  "user_data": {
    "rut": "12345678-9",
    "name": "Juan Pérez González",
    "periodo_a_validar": "2024-01"
  },
  "tipo_f30": "persona_natural",
  "response_url": "https://api.cliente.com/webhook/f30-result"
}
```

#### Ejemplo 2: Razón Social

```json
{
  "document_id": "F30-2024-002",
  "file_url": "https://storage.example.com/documents/certificado_f30_razon_social.pdf",
  "origin": "sistema-cliente-001",
  "destination": "sistema-destino-001",
  "user_data": {
    "rut": "76543210-K",
    "razon_social": "EMPRESA EJEMPLO S.A.",
    "periodo_a_validar": "2024-01"
  },
  "tipo_f30": "razon_social",
  "response_url": "https://api.cliente.com/webhook/f30-result"
}
```

---

## Response Inmediato

### Estructura del Response Inmediato

El endpoint devuelve una respuesta inmediata indicando que el documento fue recibido y está siendo procesado.

```json
{
  "message": "Certificado F30 recibido para procesamiento",
  "document_id": "string",
  "status": "PROCESSING"
}
```

### Campos del Response Inmediato

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `message` | string | Mensaje descriptivo del estado |
| `document_id` | string | ID del documento recibido |
| `status` | string | Estado inicial: siempre `"PROCESSING"` |

### Ejemplo de Response Inmediato

```json
{
  "message": "Certificado F30 recibido para procesamiento",
  "document_id": "F30-2024-001",
  "status": "PROCESSING"
}
```

---

## Response Final (Callback)

Si se proporciona `response_url`, el servicio enviará el resultado final a esa URL mediante un POST cuando el procesamiento termine.

### Estructura del Response Final

```json
{
  "document_id": "string",
  "status": "string",
  "extracted_data": {
    "campo1": "valor1",
    "campo2": "valor2"
  },
  "validation_results": [
    {
      "rule_name": "string",
      "passed": true,
      "message": "string"
    }
  ],
  "rejection_reasons": [
    {
      "reason": "string",
      "details": "string",
      "type": "string",
      "differences": []
    }
  ],
  "processing_cost_usd": 0.0,
  "processing_log": [
    "string"
  ],
  "processed_at": "2024-01-15T10:30:00.000Z"
}
```

### Campos del Response Final

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `document_id` | string | ID único del documento procesado |
| `status` | string | Decisión final: `"APPROVED"`, `"REJECTED"`, o `"MANUAL_REVIEW"` |
| `extracted_data` | object | Datos extraídos del documento mediante OCR e IA |
| `validation_results` | array | Lista de resultados de validaciones aplicadas |
| `rejection_reasons` | array | Lista de razones de rechazo (si aplica) |
| `processing_cost_usd` | float | Costo del procesamiento en USD |
| `processing_log` | array | Log detallado del procesamiento |
| `processed_at` | string | Fecha y hora de finalización (ISO 8601) |

### Estructura de `validation_results`

```json
{
  "rule_name": "string",
  "passed": true,
  "message": "string",
  "details": {}
}
```

### Estructura de `rejection_reasons`

```json
{
  "reason": "string",
  "details": "string",
  "type": "string",
  "differences": []
}
```

**Tipos de `rejection_reasons`:**
- `"data_mismatch"`: Diferencia entre documento enviado y descargado del portal
- `"download_error"`: Error en descarga automática
- `"invalid_certificate"`: Folios no válidos en portal oficial
- `"validation_failed"`: Fallo en validación cruzada
- `"authenticity_failed"`: Fallo en verificación de autenticidad

### Ejemplo de Response Final - Aprobado

```json
{
  "document_id": "F30-2024-001",
  "status": "APPROVED",
  "extracted_data": {
    "folio_oficina": "2000",
    "folio_anio": "2025",
    "folio_numero_consecutivo": "424494",
    "codigo_verificacion": "T1z57kA1",
    "nombre_solicitante": "JUAN PEREZ GONZALEZ",
    "rut_solicitante": "12345678-9",
    "domicilio": "AV. EJEMPLO 123, SANTIAGO",
    "fecha_emision": "15-01-2025",
    "estado_multas_no_boletin": "NO REGISTRA",
    "estado_deuda_previsional": "NO REGISTRA",
    "estado_resoluciones_multa": "NO REGISTRA"
  },
  "validation_results": [
    {
      "rule_name": "validar_rut",
      "passed": true,
      "message": "RUT válido y coincide con user_data"
    }
  ],
  "rejection_reasons": [],
  "processing_cost_usd": 0.0025,
  "processing_log": [
    "Documento recibido",
    "OCR completado",
    "Extracción de datos completada",
    "Validación cruzada exitosa",
    "Autenticidad verificada",
    "Descarga automática completada"
  ],
  "processed_at": "2024-01-15T10:35:42.123Z"
}
```

### Ejemplo de Response Final - Rechazado

```json
{
  "document_id": "F30-2024-002",
  "status": "REJECTED",
  "extracted_data": {
    "folio_oficina": "2000",
    "folio_anio": "2025",
    "folio_numero_consecutivo": "424494",
    "codigo_verificacion": "T1z57kA1",
    "nombre_solicitante": "JUAN PEREZ GONZALEZ",
    "rut_solicitante": "12345678-9",
    "fecha_emision": "15-01-2025"
  },
  "validation_results": [
    {
      "rule_name": "validar_rut",
      "passed": false,
      "message": "RUT no coincide con user_data"
    }
  ],
  "rejection_reasons": [
    {
      "reason": "Diferencia entre documento enviado y descargado del portal oficial",
      "details": "Se encontraron diferencias en valores críticos como RUT",
      "type": "data_mismatch",
      "differences": [
        {
          "field": "rut",
          "uploaded_value": "12345678-9",
          "downloaded_value": "98765432-1"
        }
      ]
    }
  ],
  "processing_cost_usd": 0.0025,
  "processing_log": [
    "Documento recibido",
    "OCR completado",
    "Extracción de datos completada",
    "Validación cruzada falló",
    "Documento rechazado"
  ],
  "processed_at": "2024-01-15T10:35:42.123Z"
}
```

### Ejemplo de Response Final - Revisión Manual

```json
{
  "document_id": "F30-2024-003",
  "status": "MANUAL_REVIEW",
  "extracted_data": {
    "folio_oficina": "2000",
    "folio_anio": "2025",
    "folio_numero_consecutivo": "424494",
    "codigo_verificacion": "T1z57kA1",
    "nombre_solicitante": "JUAN PEREZ GONZALEZ",
    "rut_solicitante": "12345678-9",
    "fecha_emision": "15-01-2025"
  },
  "validation_results": [
    {
      "rule_name": "validar_rut",
      "passed": true,
      "message": "RUT válido"
    }
  ],
  "rejection_reasons": [
    {
      "reason": "Descarga automática fallida - requiere revisión manual",
      "details": "Error al conectar con portal oficial",
      "type": "download_error",
      "folios_ingresados": {
        "folio_oficina": "123",
        "folio_anio": "2024",
        "folio_numero_consecutivo": "456789",
        "codigo_verificacion": "ABCD1234"
      }
    }
  ],
  "processing_cost_usd": 0.0020,
  "processing_log": [
    "Documento recibido",
    "OCR completado",
    "Extracción de datos completada",
    "Validación cruzada exitosa",
    "Error en descarga automática"
  ],
  "processed_at": "2024-01-15T10:35:42.123Z"
}
```

### Ejemplo de Response Final - Error

```json
{
  "document_id": "F30-2024-004",
  "status": "ERROR",
  "error": "Error al procesar documento: [descripción del error]",
  "processed_at": "2024-01-15T10:35:42.123Z"
}
```

---

## Códigos de Estado HTTP

### Códigos de Respuesta del Endpoint

| Código | Descripción | Cuándo Ocurre |
|--------|-------------|---------------|
| `200 OK` | Solicitud aceptada | El documento fue recibido correctamente y está siendo procesado |
| `409 Conflict` | Conflicto | El `document_id` ya está siendo procesado |
| `422 Unprocessable Entity` | Error de validación | El request no cumple con las validaciones (formato, tipo F30, etc.) |
| `500 Internal Server Error` | Error interno | Error inesperado en el servidor |

### Códigos de Respuesta del Callback

Cuando el servicio envía el resultado al `response_url`, el cliente debe responder con:

| Código | Descripción |
|--------|-------------|
| `200 OK` | Callback recibido correctamente |
| Cualquier otro | El servicio registrará un error pero no reintentará |

---

## Estados del Procesamiento

El documento pasa por diferentes estados durante el procesamiento:

| Estado | Descripción |
|--------|-------------|
| `PENDING` | Documento en cola de procesamiento |
| `OCR` | Extrayendo texto del documento con OCR |
| `CLASSIFICATION` | Clasificando el tipo de documento |
| `VALIDATION` | Ejecutando validaciones y verificaciones |
| `COMPLETED` | Procesamiento completado |
| `FAILED` | Procesamiento fallido |

---

## Decisiones Finales

El campo `status` en el response final puede tener uno de estos valores:

| Decisión | Descripción |
|----------|-------------|
| `APPROVED` | Documento aprobado. Pasó todas las validaciones y verificaciones. |
| `REJECTED` | Documento rechazado. No cumple con los requisitos o hay inconsistencias. |
| `MANUAL_REVIEW` | Requiere revisión manual. El documento pasó validaciones básicas pero hay situaciones que requieren intervención humana. |
| `ERROR` | Error durante el procesamiento. El documento no pudo ser procesado completamente. |

---

## Errores Comunes

### Error 409: Documento ya en procesamiento

```json
{
  "detail": "El documento F30-2024-001 ya está siendo procesado"
}
```

**Solución:** Esperar a que termine el procesamiento anterior o usar un `document_id` diferente.

### Error 422: Validación fallida

#### Formato de archivo inválido

```json
{
  "detail": [
    {
      "loc": ["body", "file_url"],
      "msg": "Certificado F30 solo acepta archivos PDF",
      "type": "value_error"
    }
  ]
}
```

**Solución:** Asegurarse de que el `file_url` apunte a un archivo PDF.

#### Tipo F30 inválido

```json
{
  "detail": [
    {
      "loc": ["body", "tipo_f30"],
      "msg": "tipo_f30 debe ser 'persona_natural' o 'razon_social'",
      "type": "value_error"
    }
  ]
}
```

**Solución:** Usar exactamente `"persona_natural"` o `"razon_social"`.

### Error 500: Error interno

```json
{
  "detail": "Error interno del servidor: [descripción del error]"
}
```

**Solución:** Revisar los logs del servicio.




## Ejemplos de Integración

### cURL - Request Básico

```bash
curl -X POST "https://api.example.com/api/v1/certificado_f30" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "F30-2024-001",
    "file_url": "https://storage.example.com/documents/certificado_f30.pdf",
    "origin": "sistema-cliente-001",
    "destination": "sistema-destino-001",
    "user_data": {
      "rut": "12345678-9",
      "name": "Juan Pérez González",
      "periodo_a_validar": "2024-01"
    },
    "tipo_f30": "persona_natural",
    "response_url": "https://api.cliente.com/webhook/f30-result"
  }'
```



**Última actualización:** 2024-01-15  

