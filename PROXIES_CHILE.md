# Proxies Residenciales de Chile - Recomendaciones

## ✅ **SÍ, el proxy DEBE ser de Chile**

### Por qué es crítico:

1. **Coherencia geográfica**
   - El sitio `midt.dirtrab.cl` espera conexiones desde Chile
   - Google reCAPTCHA detecta inconsistencia si la IP es de otro país
   - Headers, zona horaria, idioma deben coincidir

2. **Evita bloqueos regionales**
   - Algunos servicios bloquean IPs de otros países
   - Menor tasa de reCAPTCHA con IPs locales
   - Mejor reputación de IPs residenciales chilenas

3. **Latencia y comportamiento real**
   - Latencia baja = comportamiento más natural
   - Zona horaria correcta
   - Idioma/español de Chile

---

## 🎯 Proveedores con IPs de Chile

### 1. **Smartproxy** ⭐ RECOMENDADO
- **Ubicación**: ✅ Chile disponible
- **Tipo**: Residencial rotativo
- **Prueba**: 3 días gratis o créditos
- **Precio**: Desde ~$14/mes (plan Residential)
- **Ventajas**: 
  - Alta disponibilidad de IPs chilenas
  - Rotación automática
  - Buena reputación
- **URL**: https://smartproxy.com/
- **Configuración**: Permite seleccionar país/región específica

### 2. **SOAX**
- **Ubicación**: ✅ Chile disponible
- **Tipo**: Residencial/Móvil
- **Prueba**: Trial disponible
- **Precio**: Variable (revisar planes actuales)
- **Ventajas**:
  - Pool grande de IPs
  - Rotación automática
  - Targeting por ciudad/ISP
- **URL**: https://soax.com/proxies/locations/chile

### 3. **DataImpulse**
- **Ubicación**: ✅ Chile disponible
- **Tipo**: Residencial
- **Prueba**: Revisar en sitio
- **Precio**: Variable
- **Ventajas**: Cobertura regional local
- **URL**: https://dataimpulse.com/es/proxies-by-location/residential-proxy/cl

### 4. **Bright Data** (Premium)
- **Ubicación**: ✅ Chile disponible
- **Tipo**: Residencial/Celular/ISP
- **Prueba**: Disponible
- **Precio**: Desde $500/mes (MUY CARO)
- **Ventajas**: Muy confiable, pero demasiado caro
- **URL**: https://brightdata.com/
- **Nota**: Solo si tienes presupuesto alto

### 5. **LumiProxy**
- **Ubicación**: ✅ Chile disponible
- **Tipo**: Residencial estático/ISP
- **Prueba**: Free trial disponible
- **Precio**: Variable (revisar)
- **Ventajas**: Gran número de IPs chilenas reales
- **URL**: https://www.lumiproxy.com/cl/

---

## ❌ Proveedores SIN Chile (NO usar)

- **Webshare**: No ofrece IPs específicas de Chile (principalmente US/EU)
- Otros proveedores económicos suelen no tener Chile

---

## 🏆 RECOMENDACIÓN FINAL

### **Smartproxy - Plan Residential con targeting a Chile**

**Por qué Smartproxy:**
1. ✅ **Sí tiene IPs de Chile** (configurable por país)
2. ✅ Precio razonable (~$14/mes)
3. ✅ Prueba gratuita (3 días)
4. ✅ Residencial rotativo (mejor para reCAPTCHA)
5. ✅ Buena reputación y estabilidad

**Configuración:**
```
HTTP_PROXY=http://usuario:contraseña@gate.smartproxy.com:10000
PROXY_USER=tu_usuario
PROXY_PASSWORD=tu_contraseña
```

**Targeting**: En el dashboard de Smartproxy, selecciona:
- País: **Chile (CL)**
- Tipo: **Residential**
- Rotación: **Auto**

---

## 💰 Comparación de Precios (Chile)

| Proveedor | Precio/Mes (aprox) | IPs Chile | Prueba |
|-----------|-------------------|-----------|--------|
| **Smartproxy** | $14+ | ✅ Sí | ✅ 3 días |
| SOAX | Variable | ✅ Sí | ✅ Trial |
| DataImpulse | Variable | ✅ Sí | ⚠️ Revisar |
| LumiProxy | Variable | ✅ Sí | ✅ Trial |
| Bright Data | $500+ | ✅ Sí | ✅ Trial (caro) |

---

## ⚙️ Configuración en tu Código

Tu código **ya funciona** con cualquier proxy. Solo necesitas:

1. **Obtener cuenta en Smartproxy** (o proveedor con Chile)
2. **Configurar en `env.cloud-functions.yaml`**:
```yaml
HTTP_PROXY: "http://usuario:contraseña@gate.smartproxy.com:10000"
PROXY_USER: "tu_usuario_smartproxy"
PROXY_PASSWORD: "tu_contraseña_smartproxy"
```

3. **En el dashboard de Smartproxy**, asegúrate de:
   - Seleccionar **País: Chile**
   - Tipo: **Residential** (no datacenter)
   - Rotación: **Automática**

---

## 🔍 Verificación de IP Chilena

Para verificar que estás usando IP de Chile:

1. Con el proxy configurado, visita: https://whatismyipaddress.com/
2. Debe mostrar: **Country: Chile**
3. Si muestra otro país, ajusta la configuración en el dashboard del proxy

---

## ⚠️ Importante

- **NO uses proxies de otros países** para `midt.dirtrab.cl`
- **SÍ usa residencial rotativo** (no datacenter)
- **Combina con las mejoras anti-detección** que ya implementamos
- **Prueba primero con el trial** antes de contratar

---

## 📝 Resumen

1. ✅ **Proxy DEBE ser de Chile** (crítico)
2. ✅ **Smartproxy** es la mejor opción (precio/calidad)
3. ✅ **Residencial rotativo** (no estático)
4. ✅ Tu código ya funciona, solo configura las variables

