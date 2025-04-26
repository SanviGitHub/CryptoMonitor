"""
Punto de entrada principal para la aplicación de monitoreo de criptomonedas.
"""
import logging
import sys
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from structlog.stdlib import LoggerFactory

from app.api.router import router
from app.config import settings
from app.services.price_monitor import get_price_monitor, PriceMonitor


# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Configurar structlog para logging estructurado
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    context_class=dict,
    logger_factory=LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger("app.main")


# Clase para middleware de logging
class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware para registrar información sobre cada solicitud y respuesta HTTP.
    """
    
    async def dispatch(self, request: Request, call_next):
        start_time = structlog.get_timestamp()
        
        response = await call_next(request)
        
        process_time_ms = (structlog.get_timestamp() - start_time) * 1000
        
        logger.info(
            "Solicitud HTTP",
            method=request.method,
            url=str(request.url),
            client=request.client.host if request.client else None,
            status_code=response.status_code,
            processing_time_ms=f"{process_time_ms:.2f}ms",
        )
        
        return response


# Manejador de eventos de inicio/cierre
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Maneja eventos del ciclo de vida de la aplicación.
    """
    # Código que se ejecuta al iniciar
    logger.info("Iniciando aplicación de monitoreo de criptomonedas")
    
    # Iniciar el monitor de precios
    price_monitor = get_price_monitor()
    await price_monitor.start()
    
    yield  # Aquí la aplicación está en funcionamiento
    
    # Código que se ejecuta al cerrar
    logger.info("Deteniendo aplicación")
    await price_monitor.stop()


# Crear la aplicación FastAPI con configuración personalizada
app = FastAPI(
    title="CryptoMonitor API",
    description="""
    API para monitoreo de precios de criptomonedas en tiempo real.
    
    Esta API proporciona:
    * Monitoreo de precios de criptomonedas en tiempo real
    * Notificaciones de cambios significativos de precio
    * Cálculo de métricas estadísticas
    * WebSockets para recibir actualizaciones en tiempo real
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    debug=settings.DEBUG,
)


# Configurar middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Agregar middleware para logging
app.add_middleware(LoggingMiddleware)


# Incluir router principal
app.include_router(router)


# Manejador de excepciones global
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Manejador global de excepciones para la aplicación.
    """
    logger.exception("Error no controlado", error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": "Se produjo un error interno. Por favor, inténtelo de nuevo más tarde."},
    )


# Ruta raíz
@app.get("/")
async def root():
    """
    Endpoint raíz que redirecciona a la documentación.
    """
    return {
        "name": "CryptoMonitor API",
        "description": "API para monitoreo de precios de criptomonedas en tiempo real",
        "documentation": "/docs",
        "status": "online",
    }


# Esta sección se ejecuta solo si este archivo se ejecuta directamente
if __name__ == "__main__":
    import uvicorn
    
    # Iniciar servidor uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info" if settings.DEBUG else "warning",
    )

