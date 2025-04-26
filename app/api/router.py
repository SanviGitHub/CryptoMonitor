"""
Router principal para la API de la aplicación de monitoreo de criptomonedas.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from app.config import settings
from app.models.crypto import CryptoTick, PriceAlert, PriceSubscription, StatisticsModel
from app.services.coingecko_client import CoinGeckoClient
from app.services.price_monitor import PriceMonitor, get_price_monitor

# Configurar logger
logger = logging.getLogger(__name__)

# Crear router con prefijo definido en la configuración
router = APIRouter(prefix=settings.API_PREFIX)


@router.get("/health")
async def health_check():
    """
    Endpoint para verificar que la API está funcionando.
    """
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@router.get("/coins", response_model=List[str])
async def list_monitored_coins():
    """
    Devuelve la lista de monedas que están siendo monitoreadas.
    """
    return settings.crypto_id_list


@router.get("/prices", response_model=Dict[str, CryptoTick])
async def get_current_prices():
    """
    Devuelve los precios actuales de todas las criptomonedas monitoreadas.
    """
    price_monitor = get_price_monitor()
    
    if not price_monitor.is_running:
        raise HTTPException(
            status_code=503,
            detail="El monitor de precios no está activo. Inténtelo de nuevo más tarde."
        )
    
    return {coin_id: tick for coin_id, tick in price_monitor.latest_ticks.items()}


@router.get("/prices/{coin_id}", response_model=CryptoTick)
async def get_coin_price(
    coin_id: str = Path(..., description="ID de la criptomoneda en CoinGecko"),
):
    """
    Devuelve el precio actual de una criptomoneda específica.
    """
    price_monitor = get_price_monitor()
    
    if coin_id not in price_monitor.latest_ticks:
        raise HTTPException(
            status_code=404,
            detail=f"Criptomoneda no encontrada o no monitoreada: {coin_id}"
        )
    
    return price_monitor.latest_ticks[coin_id]


@router.get("/stats", response_model=Dict[str, StatisticsModel])
async def get_statistics():
    """
    Devuelve las estadísticas actuales de todas las criptomonedas monitoreadas.
    """
    price_monitor = get_price_monitor()
    
    if not price_monitor.latest_stats:
        raise HTTPException(
            status_code=503,
            detail="Las estadísticas aún no están disponibles"
        )
    
    return {coin_id: stats for coin_id, stats in price_monitor.latest_stats.items()}


@router.get("/stats/{coin_id}", response_model=StatisticsModel)
async def get_coin_statistics(
    coin_id: str = Path(..., description="ID de la criptomoneda en CoinGecko"),
):
    """
    Devuelve las estadísticas actuales de una criptomoneda específica.
    """
    price_monitor = get_price_monitor()
    
    if not price_monitor.latest_stats or coin_id not in price_monitor.latest_stats:
        raise HTTPException(
            status_code=404,
            detail=f"Estadísticas no disponibles para: {coin_id}"
        )
    
    return price_monitor.latest_stats[coin_id]


@router.post("/subscriptions", response_model=PriceSubscription)
async def create_subscription(subscription: PriceSubscription):
    """
    Crea una nueva suscripción para recibir alertas de cambios de precio.
    """
    price_monitor = get_price_monitor()
    
    if subscription.coin_id not in settings.crypto_id_list:
        raise HTTPException(
            status_code=400,
            detail=f"La criptomoneda {subscription.coin_id} no está en la lista de monitoreo"
        )
    
    # En una aplicación real, aquí guardaríamos la suscripción en la base de datos
    # Por ahora, simplemente la devolvemos como si se hubiera creado
    return subscription


@router.websocket("/ws/prices")
async def websocket_endpoint(websocket: WebSocket):
    """
    Endpoint WebSocket para recibir actualizaciones de precios en tiempo real.
    """
    await websocket.accept()
    
    # Clase observadora que enviará actualizaciones al WebSocket
    class WebSocketObserver:
        async def update(self, subject, **kwargs):
            if "tick" in kwargs:
                tick = kwargs["tick"]
                await websocket.send_json(tick.__dict__)
            elif "alert" in kwargs:
                alert = kwargs["alert"]
                await websocket.send_json(alert.__dict__)
    
    # Registrar observador
    price_monitor = get_price_monitor()
    observer = WebSocketObserver()
    price_monitor.register_observer(observer)
    
    try:
        # Mantener la conexión abierta
        while True:
            data = await websocket.receive_text()
            # Podríamos procesar comandos aquí si fuera necesario
    except WebSocketDisconnect:
        # Eliminar observador cuando se cierra la conexión
        price_monitor.unregister_observer(observer)

