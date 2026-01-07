#!/bin/bash
# Script para instalar dependencias del sistema en la VM

echo "=== Actualizando sistema ==="
sudo apt-get update

echo "=== Instalando dependencias del sistema para Playwright ==="
sudo apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
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
    git \
    ffmpeg

echo "=== Dependencias instaladas ==="

