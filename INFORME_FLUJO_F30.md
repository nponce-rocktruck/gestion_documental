
## Resumen 

Este documento describe el flujo completo de procesamiento de Certificados F30 (Antecedentes Laborales y Previsionales) en el sistema. El proceso está diseñado para validar la autenticidad de estos documentos, extraer información relevante, verificar su validez contra el portal oficial de la Dirección del Trabajo de Chile, y determinar si el documento cumple con todos los requisitos establecidos.

---

## 1. ¿Qué Recibe el Sistema?

### 1.1 Parámetros de Entrada

Cuando se envía un Certificado F30 para procesamiento, el sistema recibe la siguiente información:

- **document_id**: Un identificador único para el documento
- **file_url**: La URL donde se encuentra almacenado el archivo PDF del certificado
- **tipo_f30**: Tipo de certificado que puede ser:
  - `"razon_social"`: Para empresas o empleadores
  - `"persona_natural"`: Para personas naturales
- **user_data**: Datos del usuario que se utilizarán para validar que el documento corresponde a la persona o empresa correcta. Este campo es **obligatorio** para F30.
  - Para **razón social**: RUT del empleador, razón social.
  - Para **persona natural**: RUT, nombre completo.
- **origin**: Origen de la solicitud
- **destination**: Destino de la respuesta
- **response_url** (opcional): URL donde se enviará el resultado cuando termine el procesamiento

### 1.2 Validaciones Iniciales

Antes de comenzar el procesamiento, el sistema realiza las siguientes validaciones:

1. **Validación de formato**: Solo acepta archivos PDF (`.pdf`)
2. **Validación de duplicados**: Verifica que el documento no esté siendo procesado actualmente
3. **Validación de parámetros**: Confirma que `tipo_f30` sea válido (`"razon_social"` o `"persona_natural"`)
4. **Validación de datos del usuario**: Confirma que `user_data` esté presente (obligatorio para F30)

Si alguna de estas validaciones falla, el sistema rechaza la solicitud inmediatamente y devuelve un error.

---

## 2. Flujo de Procesamiento por Capas

El procesamiento se realiza en **5 capas principales**, cada una con un propósito específico. El documento debe pasar exitosamente por todas las capas para ser aprobado.

### Capa 1: OCR (Reconocimiento Óptico de Caracteres)

**¿Qué hace?**
- Descarga el archivo PDF desde la URL proporcionada
- Convierte el PDF en texto legible usando tecnología de reconocimiento óptico de caracteres
- Extrae todo el texto visible del documento

**¿Qué puede fallar?**
- El archivo no se puede descargar (URL inválida o archivo no accesible)
- El archivo no es un PDF válido
- El PDF está corrupto o protegido con contraseña
- El OCR no puede extraer texto (documento escaneado de muy baja calidad)

**Estado del documento**: `OCR`

**¿Qué pasa si falla?**
- El documento se marca como `FAILED` (fallido)
- Se registra el error en el log
- El procesamiento se detiene

---

### Capa 2: Validación y Extracción de Datos

**¿Qué hace?**
- Verifica que el documento sea realmente un Certificado F30 del tipo especificado (`razon_social` o `persona_natural`)
- Extrae automáticamente todos los datos relevantes del documento usando Inteligencia Artificial

**Datos extraídos según el tipo:**

**Para Razón Social:**
- Código del certificado (ej: `AVXYBVBONPLQ`)
- Razón social del empleador
- RUT del empleador
- RUT y nombre del representante legal
- Fecha de emisión
- Estado de multas en DTPLUS
- Estado de multas en EQUIFAX
- Estado de deuda previsional
- Detalle de deudas previsionales (si existen)

**Para Persona Natural:**
- Folio oficina (ej: `2000`)
- Folio año (ej: `2025`)
- Folio número consecutivo (ej: `424494`)
- Código de verificación (ej: `T1z57kA1`)
- Nombre del solicitante
- RUT del solicitante
- Domicilio
- Fecha de emisión
- Estado de multas ejecutoriadas
- Estado de deuda previsional
- Estado de resoluciones de multa

**¿Qué puede fallar?**
- El documento no es un Certificado F30 (es otro tipo de documento)
- El documento no corresponde al tipo especificado (se envió `persona_natural` pero es `razon_social` o viceversa)
- No se pueden extraer los datos necesarios (documento ilegible o mal formateado)
- El tipo de documento no está configurado en el sistema

**Estado del documento**: `VALIDATION`

**¿Qué pasa si falla?**
- El documento se marca como `REJECTED` (rechazado)
- Se registra la razón del rechazo
- El procesamiento se detiene (no continúa con las siguientes capas)

---

### Capa 3: Verificación de Autenticidad

**¿Qué hace?**
- Analiza el archivo PDF original en busca de señales de manipulación o falsificación
- Verifica metadatos del PDF (información técnica del archivo)
- Busca indicios de editores de PDF sospechosos
- Verifica consistencia de cabeceras HTTP y tamaño del archivo

**¿Qué busca?**
- Editores de PDF no oficiales (Adobe, Foxit, SmallPDF, iLovePDF, etc.)
- Metadatos inconsistentes
- Archivos sospechosamente pequeños o grandes
- Señales de manipulación digital

**Resultados posibles:**
- `PASSED`: No se encontraron señales de manipulación
- `WARNING`: Se encontraron algunas señales sospechosas pero no críticas
- `FAILED`: Se encontraron señales claras de manipulación

**Estado del documento**: Continúa en `VALIDATION`

**¿Qué pasa si falla?**
- Si el resultado es `FAILED`, se agrega una razón de rechazo
- Si el resultado es `WARNING`, se registra pero el documento puede continuar
- El documento puede ser marcado para revisión manual si hay sospechas

**Nota importante**: Esta capa solo se ejecuta si el documento pasó exitosamente la Capa 2. Si el documento fue rechazado en la Capa 2, esta capa se omite.

---

### Capa 4: Validación de Reglas de Negocio

**¿Qué hace?**
- Compara los datos extraídos del documento con los datos del usuario (`user_data`)
- Verifica que el RUT coincida
- Verifica que el nombre o razón social coincida (con un umbral de similitud del 85%)
- Valida reglas específicas según el tipo de F30:

**Para Razón Social:**
- ✅ El RUT del empleador debe coincidir con el RUT del usuario
- ✅ La razón social debe coincidir con el nombre/razón social del usuario
- ✅ No debe haber multas en DTPLUS (debe decir "NO REGISTRA")
- ✅ No debe haber multas en EQUIFAX (debe decir "NO REGISTRA")
- ✅ No debe haber deuda previsional (debe decir "NO REGISTRA")

**Para Persona Natural:**
- ✅ El RUT del solicitante debe coincidir con el RUT del usuario
- ✅ El nombre debe coincidir con el nombre del usuario
- ✅ No debe haber multas ejecutoriadas no incluidas en boletín
- ✅ No debe haber deuda previsional
- ✅ No debe haber resoluciones de multa

**¿Qué puede fallar?**
- El RUT no coincide
- El nombre/razón social no coincide (similitud menor al 85%)
- El documento tiene multas registradas
- El documento tiene deuda previsional
- Hay resoluciones de multa

**Estado del documento**: Continúa en `VALIDATION`

**¿Qué pasa si falla?**
- Se agregan razones de rechazo específicas para cada regla que falla
- El documento puede ser rechazado o marcado para revisión manual dependiendo de la severidad

---

### Capa 5: Descarga Automática y Verificación en Portal Oficial

**¿Qué hace?**
Esta capa solo se ejecuta si:
- El documento pasó la autenticidad (`PASSED`)
- El documento no fue rechazado en capas anteriores

El sistema accede automáticamente al portal oficial de la Dirección del Trabajo para verificar que el certificado es válido y descargar una copia oficial.

**Proceso para Razón Social:**
1. Accede al portal: `https://midt.dirtrab.cl/verificadorDocumental`
2. Ingresa el código del certificado extraído del documento
3. Verifica que el certificado sea válido
4. Si es válido, descarga el PDF oficial del portal
5. Guarda el archivo descargado en el sistema

**Proceso para Persona Natural:**
1. Accede al portal: `http://tramites.dt.gob.cl/tramitesenlinea/VerificadorTramites/VerificadorTramites.aspx`
2. Selecciona "ANTECEDENTES LABORALES Y PREVISIONALES" en el menú desplegable
3. Ingresa los folios extraídos del documento:
   - Folio oficina
   - Folio año
   - Folio número consecutivo
   - Código de verificación
4. Presiona "Buscar"
5. Verifica que el mensaje diga "El certificado es VALIDO"
6. Si es válido, descarga el PDF oficial del portal
7. Guarda el archivo descargado en el sistema

**Reintentos automáticos:**
- Si hay un error técnico (la página no carga, timeout, etc.), el sistema intenta hasta 3 veces antes de marcar como fallido

**¿Qué puede fallar?**
- Los folios/código no son válidos en el portal oficial
- El certificado no existe o fue revocado
- Error técnico al acceder al portal (página no responde, timeout, etc.)
- No se puede descargar el PDF del portal

**Estado del documento**: Continúa en `VALIDATION`

**¿Qué pasa si falla?**
- **Si los folios/código no son válidos**: El documento se marca como `REJECTED` (rechazado) con la razón "Folios no válidos en portal oficial"
- **Si hay error técnico pero el certificado es válido**: El documento se marca como `MANUAL_REVIEW` (revisión manual) con la razón "Descarga automática fallida - requiere revisión manual"
- Se registran todos los folios/códigos que se intentaron ingresar en el log

---

## 3. Estados del Documento Durante el Procesamiento

El documento pasa por los siguientes estados durante el procesamiento:

1. **PENDING**: Documento recibido, esperando procesamiento
2. **OCR**: Procesando reconocimiento óptico de caracteres
3. **VALIDATION**: Validando tipo, extrayendo datos y verificando reglas
4. **COMPLETED**: Procesamiento completado (éxito o rechazo)
5. **FAILED**: Error técnico durante el procesamiento

---

## 4. Decisiones Finales

Al finalizar todas las capas, el sistema determina una **decisión final**:

### 4.1 APPROVED (Aprobado)
**Cuándo se otorga:**
- El documento pasó todas las capas exitosamente
- No hay razones de rechazo
- La autenticidad fue verificada (`PASSED`)
- Las validaciones de reglas de negocio pasaron
- La descarga automática fue exitosa (si aplica)

**Qué significa:**
- El certificado es válido y auténtico
- Cumple con todos los requisitos
- Los datos coinciden con la información del usuario
- No tiene multas ni deudas previsionales

### 4.2 REJECTED (Rechazado)
**Cuándo se otorga:**
- El documento no es un Certificado F30 válido
- El documento no corresponde al tipo especificado
- Los datos no coinciden con la información del usuario
- El documento tiene multas o deudas previsionales
- Los folios/código no son válidos en el portal oficial
- Se detectaron señales claras de manipulación (`FAILED` en autenticidad)

**Qué significa:**
- El certificado no puede ser aceptado
- Hay problemas que impiden su aprobación
- Requiere acción del usuario (corregir datos, obtener nuevo certificado, etc.)

### 4.3 MANUAL_REVIEW (Revisión Manual)
**Cuándo se otorga:**
- Hay señales de advertencia en la autenticidad pero no son críticas
- La descarga automática falló por error técnico pero el certificado parece válido
- Hay inconsistencias menores que requieren revisión humana
- Error técnico durante el procesamiento que no permite determinar el resultado

**Qué significa:**
- El certificado necesita revisión por un operador humano
- No se puede determinar automáticamente si es válido o no
- Se requiere intervención manual para tomar una decisión

---

## 5. ¿Qué Devuelve el Sistema?

### 5.1 Respuesta Inmediata (Al Enviar la Solicitud)

Cuando se envía una solicitud de procesamiento, el sistema responde inmediatamente con:

```json
{
  "message": "Certificado F30 recibido para procesamiento",
  "document_id": "f30-12345",
  "status": "PROCESSING"
}
```

Esto significa que la solicitud fue aceptada y el procesamiento comenzará en segundo plano.

### 5.2 Resultado Final (Cuando Termina el Procesamiento)

Una vez que el procesamiento termina, el sistema devuelve:

**Información básica:**
- `document_id`: ID único del documento
- `status`: Estado final (`APPROVED`, `REJECTED`, o `MANUAL_REVIEW`)
- `processed_at`: Fecha y hora de finalización

**Datos extraídos:**
- `extracted_data`: Todos los datos extraídos del documento (RUT, nombre, fechas, estados, etc.)

**Resultados de validación:**
- `validation_results`: Lista detallada de todas las validaciones realizadas y sus resultados
- `rejection_reasons`: Lista de razones por las que el documento fue rechazado (si aplica)

**Información de autenticidad:**
- `authenticity_result`: Resultado de la verificación de autenticidad (`PASSED`, `WARNING`, `FAILED`)
- `authenticity_signals`: Señales específicas encontradas durante la verificación

**Información de descarga automática:**
- `download_automatic_result`: Resultado de la descarga automática del portal oficial
  - `success`: Si la descarga fue exitosa
  - `valid`: Si el certificado es válido en el portal
  - `message`: Mensaje descriptivo del resultado
  - `folios_ingresados`: Folios/códigos que se intentaron ingresar

**Métricas:**
- `processing_cost_usd`: Costo del procesamiento en dólares
- `processing_log`: Log detallado de todos los pasos realizados

**Ejemplo de respuesta para documento APROBADO:**

```json
{
  "document_id": "f30-12345",
  "status": "APPROVED",
  "extracted_data": {
    "codigo_certificado": "AVXYBVBONPLQ",
    "razon_social_empleador": "SOC COMERCIAL GAS MACUL LIMITADA",
    "rut_empleador": "77301140-0",
    "fecha_emision": "15-03-2025",
    "estado_multas_dtplus": "NO REGISTRA",
    "estado_multas_equifax": "NO REGISTRA",
    "estado_deuda_previsional": "NO REGISTRA"
  },
  "validation_results": [
    {
      "nombre_regla": "Coincidencia de RUT Empleador",
      "resultado": "APROBADO"
    },
    {
      "nombre_regla": "Coincidencia de Razón Social",
      "resultado": "APROBADO"
    },
    {
      "nombre_regla": "Sin Multas DTPLUS",
      "resultado": "APROBADO"
    }
  ],
  "authenticity_result": "PASSED",
  "download_automatic_result": {
    "success": true,
    "valid": true,
    "message": "Certificado descargado exitosamente del portal oficial"
  },
  "processing_cost_usd": 0.002345,
  "processed_at": "2025-01-20T15:30:45Z"
}
```

**Ejemplo de respuesta para documento RECHAZADO:**

```json
{
  "document_id": "f30-12345",
  "status": "REJECTED",
  "extracted_data": {
    "codigo_certificado": "AVXYBVBONPLQ",
    "razon_social_empleador": "OTRA EMPRESA LTDA",
    "rut_empleador": "12345678-9",
    "estado_multas_dtplus": "REGISTRA MULTAS"
  },
  "rejection_reasons": [
    {
      "reason": "Validación cruzada fallida",
      "rule": "Coincidencia de RUT Empleador",
      "details": "El RUT del documento (12345678-9) no coincide con el RUT del usuario (77301140-0)",
      "type": "cross_validation"
    },
    {
      "reason": "Regla general fallida",
      "rule": "Sin Multas DTPLUS",
      "details": "El documento registra multas en DTPLUS",
      "type": "general"
    }
  ],
  "authenticity_result": "PASSED",
  "processing_cost_usd": 0.002123,
  "processed_at": "2025-01-20T15:30:45Z"
}
```

### 5.3 Notificación Automática

Si se proporcionó un `response_url` en la solicitud, el sistema envía automáticamente el resultado final a esa URL cuando el procesamiento termina. Esto permite que sistemas externos reciban notificaciones sin necesidad de consultar constantemente el estado.

---

## 6. Errores Comunes y Sus Significados

### 6.1 Errores de Validación Inicial

- **"Certificado F30 solo acepta archivos PDF"**: Se intentó enviar un archivo que no es PDF
- **"El documento ya está siendo procesado"**: El mismo `document_id` se envió dos veces mientras aún se procesa
- **"tipo_f30 debe ser 'persona_natural' o 'razon_social'"**: Se envió un valor inválido para `tipo_f30`

### 6.2 Errores Durante el Procesamiento

- **"Error al descargar archivo"**: No se pudo descargar el PDF desde la URL proporcionada
- **"El documento no corresponde al tipo esperado"**: Se envió un documento que no es un Certificado F30 o es del tipo incorrecto
- **"No se pudieron extraer datos del documento"**: El OCR no pudo extraer información suficiente del documento
- **"Folios no válidos en portal oficial"**: Los folios/código del documento no existen o no son válidos en el portal de la Dirección del Trabajo

### 6.3 Errores de Validación

- **"Coincidencia de RUT fallida"**: El RUT en el documento no coincide con el RUT del usuario
- **"Coincidencia de Nombre/Razón Social fallida"**: El nombre/razón social no coincide (similitud menor al 85%)
- **"Regla general fallida: Sin Multas"**: El documento tiene multas registradas cuando debería decir "NO REGISTRA"
- **"Regla general fallida: Sin Deuda Previsional"**: El documento tiene deuda previsional cuando debería decir "NO REGISTRA"

### 6.4 Errores de Autenticidad

- **"Sospecha de manipulación del documento"**: Se encontraron señales de que el documento fue editado o manipulado
- **"Editor de PDF sospechoso detectado"**: El PDF fue creado o editado con un software no oficial

### 6.5 Errores de Descarga Automática

- **"Descarga automática fallida - requiere revisión manual"**: Hubo un error técnico al intentar descargar del portal, pero el certificado parece válido
- **"Error al acceder al portal oficial"**: El portal de la Dirección del Trabajo no respondió o hubo un problema de conexión

---

## 7. Flujo Visual Resumido

```
┌─────────────────────────────────────────────────────────────┐
│ 1. RECEPCIÓN DE SOLICITUD                                    │
│    - Validar formato PDF                                     │
│    - Validar parámetros                                      │
│    - Validar datos del usuario                               │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. CAPA OCR                                                  │
│    - Descargar PDF                                           │
│    - Extraer texto                                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. CAPA VALIDACIÓN Y EXTRACCIÓN                              │
│    - Verificar que sea F30 del tipo correcto                │
│    - Extraer datos del documento                             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. CAPA AUTENTICIDAD                                         │
│    - Verificar metadatos PDF                                 │
│    - Buscar señales de manipulación                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. CAPA VALIDACIÓN DE REGLAS                                │
│    - Comparar datos con user_data                            │
│    - Verificar RUT, nombre, multas, deudas                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. CAPA DESCARGA AUTOMÁTICA                                  │
│    - Verificar en portal oficial                             │
│    - Descargar PDF oficial                                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. DECISIÓN FINAL                                            │
│    - APPROVED: Todo correcto                                 │
│    - REJECTED: Problemas encontrados                         │
│    - MANUAL_REVIEW: Requiere revisión humana                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 8. Consideraciones Importantes

### 8.1 Tiempo de Procesamiento

El procesamiento completo puede tardar entre **20 a 40 segundos**, dependiendo de:
- Tamaño y complejidad del PDF
- Velocidad de respuesta del portal oficial
- Carga del sistema en el momento del procesamiento

### 8.2 Costos

Cada capa que utiliza Inteligencia Artificial tiene un costo asociado. El costo total se registra en `processing_cost_usd` .

### 8.3 Logs y Trazabilidad

Todo el proceso se registra en `processing_log`, lo que permite:
- Rastrear exactamente qué pasó en cada paso
- Identificar dónde falló un documento
- Auditar el proceso completo
- Mejorar el sistema basándose en errores comunes

### 8.4 Reintentos Automáticos

La descarga automática tiene un sistema de reintentos (hasta 3 intentos) para manejar errores temporales del portal oficial, que a veces tiene problemas de disponibilidad.

### 8.5 Seguridad

- Todos los datos se almacenan de forma segura
- Los documentos descargados del portal oficial se guardan en el sistema
- Los logs contienen información sensible y deben manejarse con cuidado

---


El sistema de procesamiento de Certificados F30 está diseñado para:
- ✅ Validar la autenticidad de los documentos
- ✅ Verificar que los datos coincidan con la información del usuario
- ✅ Confirmar que no haya multas ni deudas previsionales
- ✅ Verificar la validez en el portal oficial de la Dirección del Trabajo
- ✅ Proporcionar trazabilidad completa del proceso
- ✅ Detectar documentos falsificados o manipulados





