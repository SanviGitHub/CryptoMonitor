"""
Cliente asíncrono para interactuar con la API de CoinGecko.
"""
import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import httpx
from pydantic import ValidationError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings
from app.models.crypto import CoinGeckoMarketData, CryptoTick


logger = logging.getLogger(__name__)


class CoinGeckoAPIError(Exception):
    """Excepción para errores de la API de CoinGecko."""
    pass


class RateLimitError(CoinGeckoAPIError):
    """Excepción para errores de límite de velocidad."""
    pass


class CoinGeckoClient:
    """
    Cliente asíncrono para la API de CoinGecko con manejo de errores y reintentos.
    """
    
    def __init__(self, base_url: Optional[str] = None):
        """
        Inicializa el cliente.
        
        Args:
            base_url: URL base de la API (opcional, por defecto usa settings)
        """
        self.base_url = base_url or settings.COINGECKO_API_URL
        self.client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self) -> 'CoinGeckoClient':
        """Contexto de entrada para usar con 'async with'."""
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0,
            follow_redirects=True,
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Contexto de salida para usar con 'async with'."""
        if self.client:
            await self.client.aclose()
            self.client = None
    
    @retry(
        retry=retry_if_exception_type(
            (httpx.HTTPStatusError, httpx.ConnectTimeout, httpx.RequestError)
        ),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(5),
    )
    async def _make_request(
        self, method: str, endpoint: str, **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Realiza una solicitud HTTP a la API con manejo de errores y reintentos.
        
        Args:
            method: Método HTTP ('GET', 'POST', etc.)
            endpoint: Endpoint de la API (sin la URL base)
            **kwargs: Argumentos adicionales para httpx
        
        Returns:
            Dict con la respuesta JSON
        
        Raises:
            CoinGeckoAPIError: Si hay un error en la API
            RateLimitError: Si se alcanza el límite de velocidad
        """
        if not self.client:
            raise RuntimeError("Cliente no inicializado. Usa 'async with'.")
        
        try:
            response = await self.client.request(method, endpoint, **kwargs)
            response.raise_for_status()
            
            # Validar la respuesta
            return response.json()
        
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning("Límite de velocidad alcanzado en CoinGecko API")
                raise RateLimitError("Límite de velocidad alcanzado") from e
            
            logger.error(
                f"Error HTTP {e.response.status_code} en CoinGecko API: {e.response.text}"
            )
            raise CoinGeckoAPIError(f"Error HTTP {e.response.status_code}") from e
        
        except httpx.RequestError as e:
            logger.error(f"Error de solicitud en CoinGecko API: {str(e)}")
            raise CoinGeckoAPIError(f"Error de solicitud: {str(e)}") from e
    
    async def get_ping(self) -> bool:
        """
        Verifica que la API esté funcionando.
        
        Returns:
            True si la API responde correctamente
        """
        response = await self._make_request("GET", "/ping")
        return "gecko_says" in response
    
    async def get_price(
        self, 
        coin_ids: List[str], 
        vs_currencies: List[str] = ["usd"],
        include_market_cap: bool = True,
        include_24h_vol: bool = True,
        include_24h_change: bool = True,
    ) -> Dict[str, Dict[str, float]]:
        """
        Obtiene los precios actuales de múltiples criptomonedas.
        
        Args:
            coin_ids: Lista de IDs de criptomonedas
            vs_currencies: Lista de monedas fiat (por defecto ["usd"])
            include_market_cap: Incluir capitalización de mercado
            include_24h_vol: Incluir volumen de 24h
            include_24h_change: Incluir cambio de precio de 24h
        
        Returns:
            Dict con precios y datos adicionales
        """
        params = {
            "ids": ",".join(coin_ids),
            "vs_currencies": ",".join(vs_currencies),
            "include_market_cap": str(include_market_cap).lower(),
            "include_24hr_vol": str(include_24h_vol).lower(),
            "include_24hr_change": str(include_24h_change).lower(),
            "precision": "full",
        }
        
        return await self._make_request("GET", "/simple/price", params=params)
    
    async def get_coins_markets(
        self,
        vs_currency: str = "usd",
        ids: Optional[List[str]] = None,
        category: Optional[str] = None,
        order: str = "market_cap_desc",
        per_page: int = 100,
        page: int = 1,
        sparkline: bool = False,
        price_change_percentage: Optional[str] = "24h,7d,30d",
    ) -> List[CoinGeckoMarketData]:
        """
        Obtiene datos de mercado de múltiples criptomonedas.
        
        Args:
            vs_currency: Moneda contra la que obtener precios
            ids: Lista opcional de IDs de criptomonedas específicas
            category: Categoría opcional para filtrar resultados
            order: Orden de los resultados
            per_page: Número de resultados por página
            page: Número de página
            sparkline: Incluir datos para gráficos sparkline
            price_change_percentage: Intervalos para cambios de precio
        
        Returns:
            Lista de objetos CoinGeckoMarketData con la información de mercado
        """
        params = {
            "vs_currency": vs_currency,
            "order": order,
            "per_page": per_page,
            "page": page,
            "sparkline": str(sparkline).lower(),
        }
        
        if ids:
            params["ids"] = ",".join(ids)
        if category:
            params["category"] = category
        if price_change_percentage:
            params["price_change_percentage"] = price_change_percentage
        
        data = await self._make_request("GET", "/coins/markets", params=params)
        
        try:
            return [CoinGeckoMarketData(**item) for item in data]
        except ValidationError as e:
            logger.error("Error al validar datos de la API", error=str(e))
            raise CoinGeckoAPIError("Datos de API inválidos") from e
