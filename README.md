# Crypto Monitor

Un sistema de monitoreo de precios de criptomonedas en tiempo real utilizando el patrón Observer en Python. Este proyecto permite monitorear cambios en los precios de criptomonedas y generar alertas automáticas cuando ocurren cambios significativos.

## Características

- Monitoreo en tiempo real de precios de criptomonedas
- Sistema de alertas automáticas para cambios significativos
- Implementación del patrón Observer para manejo de eventos
- Soporte para múltiples observadores (traders, bots, análisis)
- Documentación en español
- Código asíncrono usando async/await

## Requisitos Previos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)
- Entorno virtual (recomendado)

## Instalación

1. Clona el repositorio:
   `ash
   git clone https://github.com/tu-usuario/crypto_monitor.git
   cd crypto_monitor
   `

2. Crea y activa un entorno virtual:
   `ash
   # En Windows
   python -m venv .venv
   .venv\Scripts\activate

   # En Linux/Mac
   python3 -m venv .venv
   source .venv/bin/activate
   `

3. Instala las dependencias:
   `ash
   pip install -r requirements.txt
   `

## Uso

1. Para ejecutar la demostración del sistema:
   `ash
   python demo.py
   `

2. La demostración mostrará:
   - Actualizaciones de precio en tiempo real
   - Alertas cuando los cambios son mayores al 2%
   - Simulación de múltiples observadores

## Estructura del Proyecto

`
crypto_monitor/
├── app/
│   └── models/
│       ├── observer.py     # Implementación del patrón Observer
│       └── crypto.py       # Modelos de datos para criptomonedas
├── demo.py                 # Script de demostración
├── requirements.txt        # Dependencias del proyecto
└── README.md              # Este archivo
`

## Componentes Principales

### Observer Pattern (observer.py)
- Observer: Protocolo para objetos que reciben actualizaciones
- Observable: Clase base para objetos que pueden ser observados

### Modelos de Datos (crypto.py)
- CryptoTick: Representa una actualización de precio
- PriceAlert: Representa una alerta de cambio significativo
- PriceAlertType: Tipos de alertas disponibles

### Demo (demo.py)
- MonitorPreciosBitcoin: Monitor de precios que hereda de Observable
- ObservadorPrecio: Implementación de ejemplo de un observador
- simular_cambios_precio: Función para demostrar el funcionamiento

## Ejemplo de Salida

`
[Trader] Nuevo precio de BTC: .71
[Bot Alertas] ALERTA: ¡PRICE_DECREASE! El precio de BTC disminuyó un 4.39% (.00 → .71)
`

## Personalización

Puedes crear tus propios observadores implementando la interfaz Observer:

`python
class MiObservador:
    async def update(self, subject: Observable, tick: CryptoTick = None, alert: PriceAlert = None, **kwargs):
        # Tu lógica aquí
        pass
`

## Contribuciones

Las contribuciones son bienvenidas. Por favor, asegúrate de:
1. Mantener el código en español
2. Seguir las convenciones de estilo existentes
3. Incluir docstrings y comentarios apropiados
4. Agregar tests para nuevas funcionalidades

## Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo LICENSE para más detalles.

## Contacto

Si tienes preguntas o sugerencias, no dudes en:
1. Abrir un issue
2. Enviar un pull request
3. Contactar al equipo de desarrollo

---
Si encuentras útil este proyecto, ¡no olvides darle una estrella en GitHub!
