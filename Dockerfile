FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema necesarias para Playwright/Chromium
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    libu2f-udev \
    libvulkan1 \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primero para aprovechar cache de Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instalar navegadores de Playwright (Chromium)
RUN playwright install chromium
RUN playwright install-deps chromium

# Copiar el resto del código
COPY . .

# Cloud Run expone por defecto el puerto 8080
# La variable PORT será proporcionada automáticamente por Cloud Run
ENV PORT=8080

# Exponer el puerto
EXPOSE 8080

# Usar sh -c para poder leer la variable de entorno PORT
# Asegurar que el servidor escuche correctamente en 0.0.0.0
# Cloud Run requiere que el servidor escuche en 0.0.0.0 y en el puerto especificado por PORT
# Usar --timeout-keep-alive y --limit-concurrency para mejor rendimiento
# --log-level info para ver logs de inicio
CMD sh -c "echo 'Iniciando servidor en puerto ${PORT:-8080}' && exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1 --timeout-keep-alive 30 --timeout-graceful-shutdown 10 --log-level info --no-access-log --limit-concurrency 1000"


