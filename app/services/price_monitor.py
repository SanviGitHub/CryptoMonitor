"""
Monitor de precios de criptomonedas que implementa el patrón Observer.
"""
import asyncio
import logging
from collections import deque
from datetime import datetime
from typing import Dict, List, Optional, Set, Deque

import pandas as pd
import structlog
from structlog.processors import JSONRenderer

from app.config import settings
from app.models.crypto import CryptoTick, PriceAlert, PriceAlertType, StatisticsModel
from app.models.observer import Observable
from app.services.coingecko_client import CoinGeckoClient, CoinGeckoAPIError


# Configurar logger estructurado
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        JSONRenderer(),
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger("price_monitor")


# Variable global para mantener una única instancia del monitor
_price_monitor_instance = None


def get_price_monitor() -> 'PriceMonitor':
    """
    Devuelve la instancia global del monitor de precios.
    
    Returns:
        PriceMonitor: La instancia única del monitor de precios
    """
    global _price_monitor_instance
    if _price_monitor_instance is None:
        _price_monitor_instance = PriceMonitor()
    return _price_monitor_instance


class PriceMonitor(Observable):
    """
    Monitor de precios que consulta periódicamente la API de CoinGecko
    y notifica a los observadores cuando hay cambios relevantes.
    """
    
    def __init__(self):
        """
        Inicializa el monitor de precios.
        """
        super().__init__()
        self.is_running = False
        self.crypto_ids = settings.crypto_id_list
        self.interval = settings.MONITORING_INTERVAL_SECONDS
        self.threshold = settings.PRICE_CHANGE_THRESHOLD_PERCENT
        self.buffer_size = settings.STATISTICS_BUFFER_SIZE
        
        # Almacena el último tick para cada criptomoneda
        self.latest_ticks: Dict[str, CryptoTick] = {}
        
        # Buffer circular para cada moneda para cálculos estadísticos
        self.price_history: Dict[str, Deque[CryptoTick]] = {
            coin_id: deque(maxlen=self.buffer_size) for coin_id in self.crypto_ids
        }
        
        # Últimas estadísticas calculadas
        self.latest_stats: Dict[str, StatisticsModel] = {}
        
        # Tarea de monitoreo
        self._task: Optional[asyncio.Task] = None
    
    async def start(self):
        """
        Inicia el monitoreo de precios en un bucle asíncrono.
        """
        if self.is_running:
            logger.warning("El monitor de precios ya está en ejecución")
            return
        
        self.is_running = True
        self._task = asyncio.create_task(self._monitoring_loop())
        logger.info("Monitor de precios iniciado", crypto_ids=",".join(self.crypto_ids))
    
    async def stop(self):
        """
        Detiene el monitoreo de precios.
        """
        if not self.is_running:
            return
        
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        
        logger.info("Monitor de precios detenido")
    
    async def _monitoring_loop(self):
        """
        Bucle principal que consulta precios periódicamente.
        """
        async with CoinGeckoClient() as client:
            while self.is_running:
                try:
                    await self._fetch_and_process_prices(client)
                    
                    # Calcular estadísticas si hay suficientes datos
                    await self._calculate_statistics()
                    
                except CoinGeckoAPIError as e:
                    logger.error("Error al consultar la API", error=str(e))
                except Exception as e:
                    logger.exception("Error inesperado en el monitoreo", error=str(e))
                
                # Esperar hasta la próxima consulta
                await asyncio.sleep(self.interval)
    
    async def _fetch_and_process_prices(self, client: CoinGeckoClient):
        """
        Obtiene los precios actuales y procesa las actualizaciones.
        
        Args:
            client: Cliente de CoinGecko inicializado
        """
        # Obtener precios actuales
        price_data = await client.get_price(
            self.crypto_ids,
            vs_currencies=["usd"],
            include_market_cap=True,
            include_24h_vol=True,
            include_24h_change=True
        )
        
        # Procesar cada moneda
        for coin_id in self.crypto_ids:
            if coin_id not in price_data:
                logger.warning(f"No se encontraron datos para {coin_id}")
                continue
            
            current_data = price_data[coin_id]
            
            # Crear un nuevo tick
            new_tick = CryptoTick(
                coin_id=coin_id,
                symbol=coin_id,  # Idealmente obtendríamos el símbolo real
                price_usd=current_data.get("usd", 0.0),
                market_cap_usd=current_data.get("usd_market_cap", None),
                volume_24h_usd=current_data.get("usd_24h_vol", None),
                price_change_24h_percent=current_data.get("usd_24h_change", None),
                timestamp=datetime.now()
            )
            
            # Comprobar si hay un cambio significativo
            if coin_id in self.latest_ticks:
                old_tick = self.latest_ticks[coin_id]
                percent_change = ((new_tick.price_usd - old_tick.price_usd) / old_tick.price_usd) * 100
                
                if abs(percent_change) >= self.threshold:
                    # Crear alerta de cambio de precio
                    alert_type = (
                        PriceAlertType.PRICE_INCREASE if percent_change > 0 
                        else PriceAlertType.PRICE_DECREASE
                    )
                    
                    alert = PriceAlert(
                        coin_id=coin_id,
                        symbol=new_tick.symbol,
                        alert_type=alert_type,
                        old_price_usd=old_tick.price_usd,
                        new_price_usd=new_tick.price_usd,
                        change_percent=percent_change
                    )
                    
                    # Notificar a los observadores sobre la alerta
                    await self.notify_observers(alert=alert)
                    logger.info(
                        f"Alerta de cambio de precio", 
                        coin_id=coin_id,
                        change_percent=f"{percent_change:.2f}%",
                        old_price=old_tick.price_usd,
                        new_price=new_tick.price_usd
                    )
            
            # Actualizar el tick más reciente
            self.latest_ticks[coin_id] = new_tick
            
            # Agregar al historial para cálculos estadísticos
            self.price_history[coin_id].append(new_tick)
            
            # Notificar a los observadores sobre el nuevo tick
            await self.notify_observers(tick=new_tick)
    
    async def _calculate_statistics(self):
        """
        Calcula estadísticas para cada criptomoneda basándose en el historial de precios.
        """
        for coin_id, history in self.price_history.items():
            if len(history) < 2:
                continue  # No hay suficientes datos
            
            # Crear DataFrame para cálculos
            df = pd.DataFrame([
                {
                    "price": tick.price_usd,
                    "timestamp": tick.timestamp
                } 
                for tick in history
            ])
            
            # Ordenar por timestamp
            df = df.sort_values("timestamp")
            
            # Calcular estadísticas
            try:
                # Solo calcular si hay suficientes datos
                min_periods = min(20, len(df) - 1)
                
                # Calcular SMA (Media Móvil Simple)
                if len(df) >= 20:
                    df['sma_20'] = df['price'].rolling(window=20, min_periods=min_periods).mean()
                
                # Calcular EMA (Media Móvil Exponencial)
                if len(df) >= 20:
                    df['ema_20'] = df['price'].ewm(span=20, min_periods=min_periods).mean()
                
                # Calcular volatilidad (desviación estándar)
                if len(df) >= 5:
                    # Volatilidad como porcentaje del precio
                    mean_price = df['price'].mean()
                    std = df['price'].rolling(window=min(24, len(df)), min_periods=5).std()
                    df['volatility_24h'] = (std / mean_price) * 100
                
                # Última fila para los valores más recientes
                last_row = df.iloc[-1]
                
                # Crear objeto de estadísticas
                stats = StatisticsModel(
                    coin_id=coin_id,
                    symbol=self.latest_ticks[coin_id].symbol,
                    current_price=last_row['price'],
                    sma_20=last_row.get('sma_20'),
                    ema_20=last_row.get('ema_20'),
                    volatility_24h=last_row.get('volatility_24h'),
                    timestamp=datetime.now()
                )
                
                # Actualizar estadísticas
                self.latest_stats[coin_id] = stats
                
            except Exception as e:
                logger.error(f"Error al calcular estadísticas para {coin_id}", error=str(e))
