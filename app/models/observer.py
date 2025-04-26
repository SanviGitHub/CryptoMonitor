"""
Implementación del patrón Observer para notificaciones de precios de criptomonedas.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol, Set, TypeVar

from app.models.crypto import PriceAlert, CryptoTick


class Observer(Protocol):
    """Interfaz base para observadores."""
    
    async def update(self, 
                   subject: 'Observable',
                   tick: Optional[CryptoTick] = None,
                   alert: Optional[PriceAlert] = None,
                   **kwargs: Any) -> None:
        """
        Método llamado cuando hay una actualización.
        
        Args:
            subject: El objeto observable que emitió la notificación
            tick: Opcional, nuevo tick de precio
            alert: Opcional, nueva alerta de precio
            **kwargs: Datos adicionales que podrían ser necesarios
        """
        ...


T = TypeVar('T', bound=Observer)


class Observable:
    """Clase base para objetos observables."""
    
    def __init__(self):
        """Inicializa el conjunto de observadores."""
        self._observers: Set[Observer] = set()
    
    def register_observer(self, observer: Observer) -> None:
        """
        Registra un nuevo observador.
        
        Args:
            observer: El observador a agregar
        """
        self._observers.add(observer)
    
    def unregister_observer(self, observer: Observer) -> None:
        """
        Elimina un observador.
        
        Args:
            observer: El observador a eliminar
        """
        self._observers.discard(observer)
    
    async def notify_observers(self,
                             tick: Optional[CryptoTick] = None,
                             alert: Optional[PriceAlert] = None,
                             **kwargs: Any) -> None:
        """
        Notifica a todos los observadores.
        
        Args:
            tick: Opcional, nuevo tick de precio
            alert: Opcional, nueva alerta de precio
            **kwargs: Datos adicionales para pasar a los observadores
        """
        for observer in self._observers:
            await observer.update(self, tick=tick, alert=alert, **kwargs)
