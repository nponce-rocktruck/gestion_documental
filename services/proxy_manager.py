"""
Gestor de Proxy Residencial para automatizaciones de la DT
Optimizado para reducir uso de ancho de banda
"""

import logging
import os
import requests
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class ProxyManager:
    """
    Gestiona proxies residenciales para acceso a portales que bloquean IPs de Cloud.
    Incluye tracking de uso (MB) para optimización de costos.
    """
    
    def __init__(self, proxy_config: Optional[Dict] = None):
        """
        Inicializa el gestor de proxy
        
        Args:
            proxy_config: Configuración de proxy en formato:
                {
                    'server': 'http://proxy.example.com:8080',
                    'username': 'user' (opcional),
                    'password': 'pass' (opcional)
                }
                Si es None, intenta obtenerlo de variables de entorno
        """
        self.proxy_config = proxy_config or self._get_proxy_from_env()
        self.usage_tracking = {
            "requests_count": 0,
            "total_bytes_sent": 0,
            "total_bytes_received": 0,
            "total_mb_used": 0.0,
            "last_reset": datetime.utcnow().isoformat()
        }
    
    def _get_proxy_from_env(self) -> Optional[Dict]:
        """Obtiene la configuración de proxy desde variables de entorno"""
        proxy_server = os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY")
        if proxy_server:
            proxy_config = {"server": proxy_server}
            proxy_user = os.getenv("PROXY_USER")
            proxy_pass = os.getenv("PROXY_PASSWORD")
            if proxy_user and proxy_pass:
                proxy_config["username"] = proxy_user
                proxy_config["password"] = proxy_pass
            return proxy_config
        return None
    
    def get_proxy_config(self) -> Optional[Dict]:
        """
        Obtiene la configuración de proxy para Playwright
        
        Returns:
            Dict con configuración de proxy o None si no está configurado
        """
        return self.proxy_config
    
    def is_proxy_configured(self) -> bool:
        """Verifica si hay un proxy configurado"""
        return self.proxy_config is not None
    
    def get_proxy_for_requests(self) -> Optional[Dict]:
        """
        Obtiene la configuración de proxy para la librería 'requests'
        
        Returns:
            Dict en formato {'http': '...', 'https': '...'} o None
        """
        if not self.proxy_config:
            return None
        
        server = self.proxy_config.get("server")
        if not server:
            return None
        
        username = self.proxy_config.get("username")
        password = self.proxy_config.get("password")
        
        if username and password:
            if server.startswith("http://"):
                base_url = server[7:]
                proxy_url = f"http://{username}:{password}@{base_url}"
            elif server.startswith("https://"):
                base_url = server[8:]
                proxy_url = f"https://{username}:{password}@{base_url}"
            else:
                proxy_url = f"http://{username}:{password}@{server}"
        else:
            proxy_url = server
        
        return {
            'http': proxy_url,
            'https': proxy_url
        }
    
    def track_usage(self, bytes_sent: int = 0, bytes_received: int = 0):
        """
        Registra el uso de ancho de banda del proxy
        
        Args:
            bytes_sent: Bytes enviados
            bytes_received: Bytes recibidos
        """
        self.usage_tracking["requests_count"] += 1
        self.usage_tracking["total_bytes_sent"] += bytes_sent
        self.usage_tracking["total_bytes_received"] += bytes_received
        
        total_bytes = bytes_sent + bytes_received
        total_mb = total_bytes / (1024 * 1024)
        self.usage_tracking["total_mb_used"] += total_mb
        
        logger.debug(f"Proxy usage: {total_mb:.2f} MB (sent: {bytes_sent}, received: {bytes_received})")
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de uso del proxy
        
        Returns:
            Dict con estadísticas de uso
        """
        return {
            **self.usage_tracking,
            "total_mb_used": round(self.usage_tracking["total_mb_used"], 2)
        }
    
    def reset_usage_stats(self):
        """Reinicia las estadísticas de uso"""
        self.usage_tracking = {
            "requests_count": 0,
            "total_bytes_sent": 0,
            "total_bytes_received": 0,
            "total_mb_used": 0.0,
            "last_reset": datetime.utcnow().isoformat()
        }

