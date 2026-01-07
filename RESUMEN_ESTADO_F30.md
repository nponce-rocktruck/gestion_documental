# Resumen - Afinamiento Modelo OCR Certificado F30


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

**Solución:** Revisar los logs del servicio o contactar al equipo de soporte.

---

## Flujo de Procesamiento

1. **Recepción:** El cliente envía el request al endpoint
2. **Validación:** Se valida el formato del request y se verifica que el documento no esté en procesamiento
3. **Cola:** El documento se encola para procesamiento asíncrono
4. **OCR:** Se extrae el texto del PDF
5. **Extracción:** Se extraen los datos estructurados usando IA
6. **Validación Cruzada:** Se comparan los datos extraídos con `user_data`
7. **Autenticidad:** Se verifica la autenticidad del documento
8. **Descarga Automática:** Si pasó la autenticidad, se descarga el documento original del portal oficial
9. **Comparación:** Se comparan los datos del documento enviado con el descargado
10. **Decisión Final:** Se determina si el documento es `APPROVED`, `REJECTED` o `MANUAL_REVIEW`
11. **Callback:** Si se proporcionó `response_url`, se envía el resultado final

---

## Información Adicional del Procesamiento

### Descarga Automática

Para documentos que pasan la verificación de autenticidad, el servicio ejecuta automáticamente:

1. **Descarga del portal oficial:** Descarga el documento original desde el portal de la Superintendencia
2. **Subida a la nube:** Sube el documento descargado a almacenamiento en la nube
3. **Extracción de datos:** Extrae datos del documento descargado
4. **Comparación:** Compara los datos del documento enviado con el descargado

Esta información adicional se guarda en la base de datos y puede incluir:

- `download_info`: Información sobre la descarga
- `extracted_data_downloaded`: Datos extraídos del documento descargado
- `data_comparison`: Resultado de la comparación entre documentos

### Tipos de F30

#### Persona Natural

**Campos requeridos para descarga automática:**
- `folio_oficina`: Código de la Inspección/Oficina (ej: "2000")
- `folio_anio`: Año del folio (ej: "2025")
- `folio_numero_consecutivo`: Número consecutivo único (ej: "424494")
- `codigo_verificacion`: Código alfanumérico para verificación web (ej: "T1z57kA1")

**Campos completos en `extracted_data`:**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `folio_oficina` | string | Código de la Inspección/Oficina (ubicado antes del primer '/') |
| `folio_anio` | string | Año del folio (ubicado entre los signos '/') |
| `folio_numero_consecutivo` | string | Número consecutivo único (ubicado después del último '/') |
| `codigo_verificacion` | string | Código alfanumérico para verificación web |
| `nombre_solicitante` | string | Nombre de la persona natural solicitante (Sección 1) |
| `rut_solicitante` | string | RUT de la persona natural solicitante (Sección 1) |
| `domicilio` | string | Dirección completa del solicitante |
| `fecha_emision` | string | Fecha de generación del certificado (formato dd-mm-yyyy) |
| `estado_multas_no_boletin` | string | Estado de multas ejecutoriadas no incluidas en boletín (debe ser "NO REGISTRA") |
| `estado_deuda_previsional` | string | Estado de deuda previsional (debe ser "NO REGISTRA") |
| `estado_resoluciones_multa` | string | Estado de resoluciones de multa (debe ser "NO REGISTRA") |

**Ejemplo de `extracted_data` para Persona Natural:**
```json
{
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
}
```

#### Razón Social

**Campo requerido para descarga automática:**
- `codigo_certificado`: Código único del certificado (ej: "AVXYBVBONPLQ")

**Campos completos en `extracted_data`:**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `codigo_certificado` | string | Código único del certificado ubicado en la parte superior derecha |
| `razon_social_empleador` | string | Razón social o nombre del empleador (Sección 1) |
| `rut_empleador` | string | RUT del empleador (Sección 1) |
| `rut_representante_legal` | string | RUT del representante legal (o "N/A") |
| `nombre_representante_legal` | string | Nombre del representante legal (o "N/A") |
| `fecha_emision` | string | Fecha en que se emitió el certificado (formato dd-mm-yyyy) |
| `estado_multas_dtplus` | string | Estado de multas en DTPLUS (debe ser "NO REGISTRA") |
| `estado_multas_equifax` | string | Estado de multas en EQUIFAX (debe ser "NO REGISTRA") |
| `estado_deuda_previsional` | string | Estado de deuda previsional (debe ser "NO REGISTRA") |
| `detalle_deuda_previsional` | array | Listado detallado de deudas si existieran (Institución, Monto, etc.) |

**Ejemplo de `extracted_data` para Razón Social:**
```json
{
  "codigo_certificado": "AVXYBVBONPLQ",
  "razon_social_empleador": "EMPRESA EJEMPLO S.A.",
  "rut_empleador": "76543210-K",
  "rut_representante_legal": "12345678-9",
  "nombre_representante_legal": "JUAN PEREZ GONZALEZ",
  "fecha_emision": "15-01-2025",
  "estado_multas_dtplus": "NO REGISTRA",
  "estado_multas_equifax": "NO REGISTRA",
  "estado_deuda_previsional": "NO REGISTRA",
  "detalle_deuda_previsional": []
}
```

### Validaciones Aplicadas

El servicio realiza validaciones automáticas según el tipo de F30. Estas validaciones se ejecutan contra los datos extraídos del documento y los datos proporcionados en `user_data`.

#### Validaciones para Persona Natural

1. **Coincidencia de RUT Persona**
   - Compara el RUT del solicitante en el documento con el RUT en `user_data`
   - Busca en `user_data`: `rut`, `run`, `national_id`
   - **Resultado:** Si no coincide, el documento es rechazado

2. **Coincidencia de Nombre**
   - Compara el nombre en el documento con el nombre en `user_data`
   - Busca en `user_data`: `name`, `full_name`
   - Usa umbral de similitud del 85% (permite diferencias menores de formato)
   - **Resultado:** Si la similitud es menor al 85%, el documento es rechazado

3. **Validación de Fecha (Mes Vencido)**
   - Verifica que el certificado haya sido emitido en el mes siguiente al período validado
   - Usa `periodo_a_validar` de `user_data` como referencia
   - **Resultado:** Si la fecha no cumple el criterio, el documento es rechazado

4. **Sin Multas Ejecutoriadas (No Boletín)**
   - Verifica que `estado_multas_no_boletin` sea "NO REGISTRA"
   - **Resultado:** Si hay multas, el documento es rechazado

5. **Sin Deuda Previsional**
   - Verifica que `estado_deuda_previsional` sea "NO REGISTRA"
   - **Resultado:** Si hay deuda, el documento es rechazado

6. **Sin Resoluciones de Multa**
   - Verifica que `estado_resoluciones_multa` sea "NO REGISTRA"
   - **Resultado:** Si hay resoluciones de multa, el documento es rechazado

#### Validaciones para Razón Social

1. **Coincidencia de RUT Empleador**
   - Compara el RUT del empleador en el documento con el RUT en `user_data`
   - Busca en `user_data`: `rut`, `run`, `tax_id`
   - **Resultado:** Si no coincide, el documento es rechazado

2. **Coincidencia de Razón Social**
   - Compara la razón social en el documento con la razón social en `user_data`
   - Busca en `user_data`: `name`, `business_name`, `razon_social`
   - Usa umbral de similitud del 85% (permite diferencias menores de formato)
   - **Resultado:** Si la similitud es menor al 85%, el documento es rechazado

3. **Validación de Fecha (Mes Vencido)**
   - Verifica que el certificado haya sido emitido en el mes siguiente al período validado
   - Usa `periodo_a_validar` de `user_data` como referencia
   - **Resultado:** Si la fecha no cumple el criterio, el documento es rechazado

4. **Sin Multas DTPLUS**
   - Verifica que `estado_multas_dtplus` sea "NO REGISTRA"
   - **Resultado:** Si hay multas, el documento es rechazado

5. **Sin Multas EQUIFAX**
   - Verifica que `estado_multas_equifax` sea "NO REGISTRA"
   - **Resultado:** Si hay multas, el documento es rechazado

6. **Sin Deuda Previsional**
   - Verifica que `estado_deuda_previsional` sea "NO REGISTRA"
   - **Resultado:** Si hay deuda, el documento es rechazado

**Nota:** Todas las validaciones deben pasar para que el documento sea aprobado. Si alguna falla, el documento será rechazado y se incluirá la razón en `rejection_reasons`.

---

## Notas de Implementación

1. **Procesamiento Asíncrono:** El endpoint devuelve inmediatamente. El procesamiento ocurre en background.

2. **Timeout del Callback:** El servicio espera hasta 30 segundos para recibir respuesta del callback. Si no hay respuesta o hay error, se registra en logs pero no se reintenta.

3. **Idempotencia:** El mismo `document_id` no puede procesarse simultáneamente. Si se intenta, se devuelve error 409.

4. **Formato de Fechas:** Todas las fechas en las respuestas están en formato ISO 8601 (UTC).

5. **Costo del Procesamiento:** El campo `processing_cost_usd` incluye los costos de OCR y procesamiento con IA.

---

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


## Seguridad

1. **Autenticación:** El servicio puede requerir autenticación mediante tokens o API keys (configuración dependiente del despliegue).

2. **HTTPS:** Todas las comunicaciones deben realizarse sobre HTTPS.

3. **Validación de URLs:** El servicio valida que las URLs proporcionadas sean accesibles y válidas.

4. **Rate Limiting:** Puede haber límites de tasa de solicitudes por cliente (configuración dependiente del despliegue).

---

## Límites y Restricciones

1. **Tamaño de archivo:** El tamaño máximo del PDF está limitado por la configuración del servidor (típicamente 10-50 MB).

2. **Timeout:** El procesamiento tiene un timeout máximo (típicamente 5-10 minutos).

3. **Concurrencia:** El número de documentos procesados simultáneamente puede estar limitado.

---

## Soporte y Contacto

Para problemas o consultas sobre la API, contactar al equipo de desarrollo o revisar los logs del servicio.

---

**Última actualización:** 2024-01-15  






-----------------

-------------
---------------
---------------
----------
## ✅ Avances

- **Validación exhaustiva**: Revisando documento por documento para identificar patrones y ajustar reglas
- **Mejoras en detección**: Ampliada la lista de editores PDF detectados (Adobe, Foxit, SmallPDF, iLovePDF, etc.)
- **Ajustes en metadatos**: Refinadas las validaciones de cabeceras HTTP, EXIF y metadatos PDF

## ⚠️ Problema Encontrado

**Caso específico:**
- Documento que **pasa todas las validaciones de metadatos** pero visualmente está **"cortado"**
- URL: `https://storage.googleapis.com/rocktruck-prd/binnacle/-1756780754086_f30 ruth aguayo.pdf-2-9-2025 2:39:14.pdf`
- **Conclusión**: Las validaciones de metadatos tienen límites; no detectan manipulaciones visuales sofisticadas

## 🔍 Solución Propuesta

**Verificación de código en portal oficial** (https://midt.dirtrab.cl/verificadorDocumental):
- Validación directa con la fuente oficial
- Detecta falsificaciones incluso si los metadatos son correctos
- **Requiere**: Invertir el orden del proceso (extraer código → verificar → continuar)
- **Estado**: Investigando si existe API disponible

## 📋 Próximos Pasos

1. Investigar disponibilidad de API para verificación de código
2. Evaluar viabilidad de implementación
3. Ajustar pipeline de procesamiento si es viable

---

**Estado**: 🔄 En desarrollo activo | **Última actualización**: 20/11/2025



nos centraremos en el F30, luego vere la logica de los otros tipos de documentos
la logica del f30 cambiará esto es todo el proceso 

- necesito agregar un parametro más, algo que distinga si es persona natural o razón social al request y los datos del usuario siempre seran requeridos 
- siempre se debe validar que sea un pdf
- debe pasar por la capa de ocr
- luego se debe validar y extraer los datos, se agregará un nuevo tipo de documento, que corresponde al f30 pero para persona natural, el que está es para raon social, se trataran de distinta manera. validar que si corresponde al documento que menciona el nuevo parametro
    - tipos de f30 :
        este es el que tengo, que corresponde a f30 razon social, no necesito que lo inicialices en el codigo ni nada de eso, no ensucies el codigo con estas cosas de bbdd, elimina todo lo que inicie cosas de este tipo en bbdd desde el codigo, tanto en local, como desarrollo, continuo:

                    {
            "_id": {
                "$oid": "691f0926e8f26643ebcc8e81"
            },
            "name": "Certificado F30 - Antecedentes Laborales y Previsionales - Razón Social",
            "country": "CL",
            "description": "Certificado emitido por la Dirección del Trabajo de Chile que acredita los antecedentes laborales y previsionales de un empleador (Razón Social).",
            "extraction_schema": {
                "codigo_certificado": {
                "type": "string",
                "description": "Código único del certificado ubicado en la parte superior derecha (Ej: AVXYBVBONPLQ)."
                },
                "razon_social_empleador": {
                "type": "string",
                "description": "Razón social o nombre del empleador indicado en la sección 1."
                },
                "rut_empleador": {
                "type": "string",
                "description": "RUT del empleador indicado en la sección 1."
                },
                "rut_representante_legal": {
                "type": "string",
                "description": "RUT del representante legal si aplica (o N/A)."
                },
                "nombre_representante_legal": {
                "type": "string",
                "description": "Nombre del representante legal si aplica (o N/A)."
                },
                "fecha_emision": {
                "type": "date_dd-mm-yyyy",
                "description": "Fecha en que se emitió el certificado (Sección 3)."
                },
                "estado_multas_dtplus": {
                "type": "string",
                "description": "Texto que indica el estado de multas en DTPLUS. Debe extraerse 'NO REGISTRA' si no hay multas."
                },
                "estado_multas_equifax": {
                "type": "string",
                "description": "Texto que indica el estado de multas en EQUIFAX. Debe extraerse 'NO REGISTRA' si no hay multas."
                },
                "estado_deuda_previsional": {
                "type": "string",
                "description": "Texto bajo la sección DEUDA PREVISIONAL. Debe extraerse 'NO REGISTRA' si no hay deuda."
                },
                "detalle_deuda_previsional": {
                "type": "array",
                "description": "Listado detallado de deudas si existieran (Institución, Monto, etc).",
                "items": {
                    "type": "object",
                    "properties": {
                    "institucion": { "type": "string" },
                    "monto": { "type": "number" }
                    }
                }
                }
            },
            "general_rules": [
                {
                "description": "Para los campos de estado (estado_multas_dtplus, estado_multas_equifax, estado_deuda_previsional), si el documento dice explícitamente 'NO REGISTRA', extraer ese valor exacto."
                }
            ],
            "validation_rules": [
                {
                "rule_name": "Coincidencia de RUT Empleador",
                "rule_type": "identity_match",
                "description": "El RUT del empleador en el documento debe coincidir con el RUT del usuario.",
                "document_field": "rut_empleador",
                "user_data_concepts": [
                    "rut",
                    "run",
                    "tax_id"
                ]
                },
                {
                "rule_name": "Coincidencia de Razón Social",
                "rule_type": "text_match",
                "description": "La Razón Social del documento debe coincidir con el nombre o razón social del usuario.",
                "document_field": "razon_social_empleador",
                "user_data_concepts": [
                    "name",
                    "business_name",
                    "razon_social"
                ],
                "match_threshold": 0.85
                },
                {
                "rule_name": "Sin Multas DTPLUS",
                "rule_type": "value_match",
                "description": "El documento no debe presentar multas en el boletín DTPLUS.",
                "document_field": "estado_multas_dtplus",
                "expected_value": "NO REGISTRA",
                "operator": "equals_case_insensitive"
                },
                {
                "rule_name": "Sin Multas EQUIFAX",
                "rule_type": "value_match",
                "description": "El documento no debe presentar multas en el boletín EQUIFAX.",
                "document_field": "estado_multas_equifax",
                "expected_value": "NO REGISTRA",
                "operator": "equals_case_insensitive"
                },
                {
                "rule_name": "Sin Deuda Previsional",
                "rule_type": "value_match",
                "description": "El documento no debe presentar deuda previsional vigente.",
                "document_field": "estado_deuda_previsional",
                "expected_value": "NO REGISTRA",
                "operator": "equals_case_insensitive"
                }
            ],
            "is_active": true,
            "created_at": {
                "$date": "2025-11-20T12:32:41.102Z"
            },
            "updated_at": {
                "$date": "2025-07-05T14:00:00.000Z"
            }
            }



            y este es el f30 de persona natural

            {
  "_id": {
    "$oid": "691f0926e8f26643ebcc8e82"
  },
  "name": "Certificado F30 - Antecedentes Laborales y Previsionales - Persona Natural",
  "country": "CL",
  "description": "Certificado emitido por la Dirección del Trabajo de Chile para Personas Naturales, acreditando antecedentes laborales y previsionales.",
  "extraction_schema": {
    "folio_oficina": {
      "type": "string",
      "description": "Primer número del folio, correspondiente al código de la Inspección/Oficina (ubicado antes del primer '/'). Ej: 2000."
    },
    "folio_anio": {
      "type": "string",
      "description": "Segundo número del folio, correspondiente al año (ubicado entre los signos '/'). Ej: 2025."
    },
    "folio_numero_consecutivo": {
      "type": "string",
      "description": "Tercer número del folio, correspondiente al consecutivo único (ubicado después del último '/'). Ej: 424494."
    },
    "codigo_verificacion": {
      "type": "string",
      "description": "Código alfanumérico ubicado generalmente al final del documento para verificación web (Ej: T1z57kA1)."
    },
    "nombre_solicitante": {
      "type": "string",
      "description": "Nombre de la persona natural solicitante (Sección 1, Razón Social / Nombre)."
    },
    "rut_solicitante": {
      "type": "string",
      "description": "RUT de la persona natural solicitante (Sección 1)."
    },
    "domicilio": {
      "type": "string",
      "description": "Dirección completa del solicitante."
    },
    "fecha_emision": {
      "type": "date_dd-mm-yyyy",
      "description": "Fecha de generación del certificado (ubicada usualmente en el pie de página)."
    },
    "estado_multas_no_boletin": {
      "type": "string",
      "description": "Estado bajo la sección 'MULTAS EJECUTORIADAS - NO INCLUIDAS EN BOLETÍN'. Debe extraerse 'NO REGISTRA'."
    },
    "estado_deuda_previsional": {
      "type": "string",
      "description": "Estado bajo la sección 'DEUDA PREVISIONAL (BOLETIN DE INFRACTORES)'. Debe extraerse 'NO REGISTRA'."
    },
    "estado_resoluciones_multa": {
      "type": "string",
      "description": "Estado bajo la sección 'RESOLUCIONES DE MULTA (BOLETIN DE INFRACTORES)'. Debe extraerse 'NO REGISTRA'."
    }
  },
  "general_rules": [
    {
      "description": "Al extraer los estados de deuda o multas, eliminar guiones decorativos (ej: '-- NO REGISTRA --' debe extraerse como 'NO REGISTRA')."
    },
    {
      "description": "Si existen multas o deudas, extraer el detalle completo (Monto, Institución) en lugar del estado."
    }
  ],
  "validation_rules": [
    {
      "rule_name": "Coincidencia de RUT Persona",
      "rule_type": "identity_match",
      "description": "El RUT del solicitante en el documento debe coincidir con el RUT del usuario.",
      "document_field": "rut_solicitante",
      "user_data_concepts": [
        "rut",
        "run",
        "national_id"
      ]
    },
    {
      "rule_name": "Coincidencia de Nombre",
      "rule_type": "text_match",
      "description": "El nombre en el documento debe coincidir con el nombre del usuario.",
      "document_field": "nombre_solicitante",
      "user_data_concepts": [
        "name",
        "full_name"
      ],
      "match_threshold": 0.85
    },
    {
      "rule_name": "Sin Multas Ejecutoriadas (No Boletín)",
      "rule_type": "value_match",
      "description": "No deben existir multas ejecutoriadas no incluidas en el boletín.",
      "document_field": "estado_multas_no_boletin",
      "expected_value": "NO REGISTRA",
      "operator": "contains_case_insensitive"
    },
    {
      "rule_name": "Sin Deuda Previsional",
      "rule_type": "value_match",
      "description": "No debe existir deuda previsional vigente.",
      "document_field": "estado_deuda_previsional",
      "expected_value": "NO REGISTRA",
      "operator": "contains_case_insensitive"
    },
    {
      "rule_name": "Sin Resoluciones de Multa",
      "rule_type": "value_match",
      "description": "No deben existir resoluciones de multa en el boletín.",
      "document_field": "estado_resoluciones_multa",
      "expected_value": "NO REGISTRA",
      "operator": "contains_case_insensitive"
    }
  ],
  "is_active": true,
  "created_at": {
    "$date": "2025-11-20T14:15:00.000Z"
  },
  "updated_at": {
    "$date": "2025-11-20T14:15:00.000Z"
  }
}

elimina del codigo authenticity_config, creo que ya no lo uso


una vez que se valide con alta precision que es el documento y se extraiga la data deben pasar por la capa para saber si han sido intervenidos 

si pasa bien necesito que pase por la capa donde se automatiza la descarga del documento original, ya tengo automatizada si es para razon social, si es para persona natural es asi la automatizacion 

http://tramites.dt.gob.cl/tramitesenlinea/VerificadorTramites/VerificadorTramites.aspx

luego selecciona aca 

<select name="ctl00$cphTramite$ddlTipoTramite" onchange="javascript:setTimeout('__doPostBack(\'ctl00$cphTramite$ddlTipoTramite\',\'\')', 0)" id="ctl00_cphTramite_ddlTipoTramite" class="caja">
	<option value="-1">-- SELECCIONE TIPO DE TRAMITE --</option>
	<option selected="selected" value="2">ANTECEDENTES LABORALES Y PREVISIONALES</option>
	<option value="8">CERTIFICADO DE CUMPLIMIENTO DE OBLIGACIONES LABORALES Y PREVISIONALES</option>
	<option value="4">CERTIFICADO DE ORGANIZACIONES SINDICALES</option>
	<option value="6">CERTIFICADO DE CONSTANCIA PARA TRABAJADORES</option>
	<option value="7">CERTIFICADO DE INGRESO DE LICENCIA MEDICA</option>
	<option value="9">CONTRATO DE TRABAJADOR/A DE CASA PARTICULAR</option>

</select>

te dejo el full path tbn /html/body/form/div[3]/div[3]/div[3]/div[2]/table/tbody/tr[1]/td[2]/select

ANTECEDENTES LABORALES Y PREVISIONALES

despues
escribir 
"folio_oficina" aca
<input name="ctl00$cphTramite$tbICT" type="text" value="2000" size="9" id="ctl00_cphTramite_tbICT" class="caja">
/html/body/form/div[3]/div[3]/div[3]/div[2]/table/tbody/tr[2]/td[2]/input[1]

luego "folio_anio" 
<input name="ctl00$cphTramite$tbAgno" type="text" value="2025" size="8" id="ctl00_cphTramite_tbAgno" class="caja">
/html/body/form/div[3]/div[3]/div[3]/div[2]/table/tbody/tr[2]/td[2]/input[2]

y aca "folio_numero_consecutivo"
<input name="ctl00$cphTramite$tbCorre" type="text" value="424494" size="9" id="ctl00_cphTramite_tbCorre" class="caja">
/html/body/form/div[3]/div[3]/div[3]/div[2]/table/tbody/tr[2]/td[2]/input[3]


aca "codigo_verificacion"
<input name="ctl00$cphTramite$tbCodVerificacion" type="text" value="T1z57kA1" size="50" id="ctl00_cphTramite_tbCodVerificacion" class="caja">
/html/body/form/div[3]/div[3]/div[3]/div[2]/table/tbody/tr[3]/td[2]/input

luego presionar buscar 

<input type="submit" name="ctl00$cphTramite$btnBuscar" value="Buscar" id="ctl00_cphTramite_btnBuscar" class="boton">

esperar 

si dice aca El certificado es VALIDO

<span id="ctl00_cphTramite_lblMensaje" style="color:Red;font-size:12pt;">El certificado es VALIDO.<br></span>

presionar <input type="image" name="ctl00$cphTramite$ibtnHTMLC2" id="ctl00_cphTramite_ibtnHTMLC2" src="../Imagenes/descargaPDF.gif" style="border-width:0px;">

sino marcar como resicion manual 
folios no validos y loguear los folios que se escribieron 

esta pagina simpre tiene problemas por lo que necesito re ejecutar en caso de error que no cargue algo, unas 3 veces 
necesito descargar el documento

necesito loguar absolutamente todo en bbdd 

y necesito que la logica quede lo mas ordenada y estructurada posibñle para este tipo de documento, que son 2 finalmente dependiendo si es razon social o persona natural






