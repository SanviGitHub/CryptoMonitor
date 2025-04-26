"""
Demo del patrón Observer para monitoreo de precios de criptomonedas.
"""
import asyncio
import random
from datetime import datetime

from app.models.observer import Observer, Observable
from app.models.crypto import CryptoTick, PriceAlert, PriceAlertType


class MonitorPreciosBitcoin(Observable):
    """
    Monitor de precios de Bitcoin que notifica a los observadores
    cuando ocurren cambios significativos en el precio.
    """
    
    def __init__(self):
        """Inicializa el monitor con un precio base."""
        super().__init__()
        self.precio_actual = 50000.0  # Precio inicial en USD
        self.coin_id = "bitcoin"
        self.symbol = "BTC"
        self.ultimo_tick = None
    
    async def actualizar_precio(self, nuevo_precio: float):
        """
        Actualiza el precio y notifica a los observadores si es necesario.
        
        Args:
            nuevo_precio: El nuevo precio de Bitcoin en USD
        """
        precio_anterior = self.precio_actual
        cambio_porcentual = ((nuevo_precio - precio_anterior) / precio_anterior) * 100
        
        # Crear un nuevo tick con los datos actualizados
        tick = CryptoTick(
            coin_id=self.coin_id,
            symbol=self.symbol,
            price_usd=nuevo_precio,
            price_change_24h_percent=cambio_porcentual,
            timestamp=datetime.now()
        )
        self.ultimo_tick = tick
        self.precio_actual = nuevo_precio
        
        # Notificar a todos los observadores sobre el nuevo tick
        await self.notify_observers(tick=tick)
        
        # Si el cambio es significativo (>2%), generar una alerta
        if abs(cambio_porcentual) > 2.0:
            alert_type = (
                PriceAlertType.PRICE_INCREASE if cambio_porcentual > 0 
                else PriceAlertType.PRICE_DECREASE
            )
            
            alerta = PriceAlert(
                coin_id=self.coin_id,
                symbol=self.symbol,
                alert_type=alert_type,
                old_price_usd=precio_anterior,
                new_price_usd=nuevo_precio,
                change_percent=cambio_porcentual
            )
            
            # Notificar a los observadores sobre la alerta
            await self.notify_observers(alert=alerta)


class ObservadorPrecio:
    """
    Observador que recibe y maneja actualizaciones de precio y alertas.
    """
    
    def __init__(self, nombre: str):
        """
        Inicializa el observador con un nombre para identificarlo.
        
        Args:
            nombre: Nombre del observador
        """
        self.nombre = nombre
    
    async def update(self, 
                  subject: Observable,
                  tick: CryptoTick = None,
                  alert: PriceAlert = None,
                  **kwargs):
        """
        Procesa las actualizaciones del precio.
        
        Args:
            subject: El monitor de precios que envió la notificación
            tick: Información de precio actualizada
            alert: Alerta de precio si se generó una
        """
        if tick:
            print(f"[{self.nombre}] Nuevo precio de {tick.symbol}: ${tick.price_usd:.2f}")
            
        if alert:
            print(f"[{self.nombre}] ⚠️ ALERTA: {alert.message}")


async def simular_cambios_precio():
    """
    Simula cambios de precio aleatorios para demostrar el patrón Observer.
    """
    # Crear el monitor de precios (Observable)
    monitor = MonitorPreciosBitcoin()
    
    # Crear y registrar observadores
    trader = ObservadorPrecio("Trader")
    analista = ObservadorPrecio("Analista")
    bot_alertas = ObservadorPrecio("Bot Alertas")
    
    # Registrar observadores
    monitor.register_observer(trader)
    monitor.register_observer(analista)
    monitor.register_observer(bot_alertas)
    
    print("Comenzando simulación de mercado de Bitcoin...")
    
    # Simular 10 cambios de precio
    for i in range(1, 11):
        # Generar una variación aleatoria entre -5% y +5%
        variacion = random.uniform(-5.0, 5.0)
        nuevo_precio = monitor.precio_actual * (1 + variacion/100)
        
        print(f"\n--- Actualización {i} ---")
        await monitor.actualizar_precio(nuevo_precio)
        
        # Dar de baja al analista después de 5 actualizaciones
        if i == 5:
            print("\n[Sistema] El Analista ha dejado de observar los precios.")
            monitor.unregister_observer(analista)
            
        # Pausa entre actualizaciones
        await asyncio.sleep(1)


if __name__ == "__main__":
    # Ejecutar la simulación
    print("Demostrando el patrón Observer para monitoreo de criptomonedas\n")
    asyncio.run(simular_cambios_precio())

