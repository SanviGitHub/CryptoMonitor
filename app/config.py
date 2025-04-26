"""
Configuración de la aplicación de monitoreo de criptomonedas.
"""
import os
from typing import Dict, List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuración de la aplicación cargada desde variables de entorno o .env
    """
    # Base de la API
    COINGECKO_API_URL: str = "https://api.coingecko.com/api/v3"
    
    # Configuración de monitoreo
    MONITORING_INTERVAL_SECONDS: int = Field(default=30, ge=5)
    PRICE_CHANGE_THRESHOLD_PERCENT: float = Field(default=1.0, ge=0.1)
    
    # Criptomonedas a monitorear (ids de coingecko, separados por comas)
    CRYPTO_IDS: str = "bitcoin,ethereum,cardano,solana,polkadot"
    
    # Tamaño del buffer para cálculos estadísticos
    STATISTICS_BUFFER_SIZE: int = Field(default=100, ge=10)
    
    # Configuración de la base de datos
    DATABASE_URL: str = "sqlite:///./crypto_monitor.db"
    
    # Configuración de FastAPI
    API_PREFIX: str = "/api"
    DEBUG: bool = True
    
    @property
    def crypto_id_list(self) -> List[str]:
        """
        Lista de IDs de criptomonedas a monitorear.
        """
        return [cid.strip() for cid in self.CRYPTO_IDS.split(",") if cid.strip()]
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


# Instancia global de configuración
settings = Settings()

