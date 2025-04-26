"""
Modelos de datos para información de criptomonedas.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator


class PriceAlertType(str, Enum):
    """Tipos de alertas de precio"""
    PRICE_INCREASE = "price_increase"
    PRICE_DECREASE = "price_decrease"
    VOLATILITY = "volatility"
    VOLUME_SPIKE = "volume_spike"
    MARKET_CAP_CHANGE = "market_cap_change"


@dataclass
class CryptoTick:
    """
    Representa un único registro de precio de criptomoneda en un momento dado.
    """
    coin_id: str
    symbol: str
    price_usd: float
    market_cap_usd: Optional[float] = None
    volume_24h_usd: Optional[float] = None
    price_change_24h_percent: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PriceAlert:
    """
    Alerta generada cuando el precio cumple ciertas condiciones.
    """
    coin_id: str
    symbol: str
    alert_type: PriceAlertType
    old_price_usd: float
    new_price_usd: float
    change_percent: float
    timestamp: datetime = field(default_factory=datetime.now)
    message: str = field(init=False)
    
    def __post_init__(self):
        """Genera el mensaje de alerta automáticamente"""
        direction = "aumentó" if self.change_percent > 0 else "disminuyó"
        self.message = (
            f"¡{self.alert_type.value.upper()}! El precio de {self.symbol.upper()} "
            f"{direction} un {abs(self.change_percent):.2f}% "
            f"(${self.old_price_usd:.2f} → ${self.new_price_usd:.2f})"
        )


class StatisticsModel(BaseModel):
    """
    Modelo para estadísticas calculadas sobre precios.
    """
    coin_id: str
    symbol: str
    current_price: float
    sma_20: Optional[float] = None  # Media móvil simple de 20 períodos
    ema_20: Optional[float] = None  # Media móvil exponencial de 20 períodos
    volatility_24h: Optional[float] = None  # Desviación estándar de 24h (%)
    rsi_14: Optional[float] = None  # Índice de fuerza relativa (14 períodos)
    timestamp: datetime = Field(default_factory=datetime.now)


class CoinGeckoMarketData(BaseModel):
    """Modelo para datos de mercado de CoinGecko"""
    id: str
    symbol: str
    name: str
    current_price: Dict[str, float]
    market_cap: Dict[str, float]
    market_cap_rank: Optional[int] = None
    total_volume: Dict[str, float]
    price_change_percentage_24h: Optional[float] = None
    price_change_percentage_7d: Optional[float] = None
    price_change_percentage_30d: Optional[float] = None


class PriceSubscription(BaseModel):
    """
    Suscripción a actualizaciones de precio de una criptomoneda.
    """
    coin_id: str
    min_change_percent: float = 1.0
    user_id: Optional[str] = None
    active: bool = True
