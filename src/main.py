import logging
from contextlib import asynccontextmanager
import time
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from core.config import get_config
from utils.metrics import setup_metrics, track_in_progress, record_api_request
from routes import base_router, parser_router

settings = get_config()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting up...")
    yield
    logger.info("Application shutting down...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API for parsing English job descriptions using vLLM",
    version="1.0.0",
    docs_url="/api/docs",          # Swagger UI  
    redoc_url="/api/redoc",        # ReDoc UI
    openapi_url="/api/openapi.json", # JSON Schema 
    lifespan=lifespan,
)

setup_metrics(app, enabled=settings.ENABLE_METRICS)

@app.middleware("http")
async def prometheus_custom_metrics_middleware(request: Request, call_next):
    route = request.scope.get("route")
    route_path = route.path if route else request.url.path
    method = request.method
    
    with track_in_progress(route=route_path, method=method):
        start_time = time.perf_counter() 
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            status_code = 500
            raise
        finally:
            duration = time.perf_counter() - start_time
            record_api_request(
                route=route_path,
                method=method,
                status_code=status_code,
                duration_seconds=duration
            )
            
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s", request.url)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred."},
    )


app.include_router(base_router)
app.include_router(parser_router)