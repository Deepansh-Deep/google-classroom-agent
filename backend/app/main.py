"""
Google Classroom Smart Assistant - Main Application Entry Point

Production-ready FastAPI application with:
- CORS configuration
- Middleware setup
- Exception handling
- API routing
- Health checks
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.api.v1.router import api_router
from app.core.exceptions import AppException
from app.utils.logging import setup_logging, get_logger

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup and shutdown events."""
    # Startup
    setup_logging()
    logger.info("Starting Google Classroom Smart Assistant", version="1.0.0")
    
    # Initialize database connections
    from app.models.database import init_db
    await init_db()
    logger.info("Database connections established")
    
    # Initialize vector store
    from app.integrations.vector_store import init_vector_store
    await init_vector_store()
    logger.info("Vector store initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application")
    from app.models.database import close_db
    await close_db()


def create_application() -> FastAPI:
    """Factory function to create and configure the FastAPI application."""
    
    app = FastAPI(
        title="Google Classroom Smart Assistant",
        description="AI-powered classroom management with intelligent Q&A and analytics",
        version="1.0.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        openapi_url="/openapi.json" if settings.debug else None,
        lifespan=lifespan,
    )
    
    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API router
    app.include_router(api_router, prefix="/api/v1")
    
    # Global exception handler
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.error_code,
                "message": exc.message,
                "details": exc.details,
            },
        )
    
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception", exc_info=exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "internal_error",
                "message": "An unexpected error occurred",
            },
        )
    
    # Health check endpoint
    @app.get("/health", tags=["Health"])
    async def health_check():
        """Health check endpoint for load balancers and monitoring."""
        return {
            "status": "healthy",
            "version": "1.0.0",
            "environment": settings.app_env,
        }
    
    @app.get("/ready", tags=["Health"])
    async def readiness_check():
        """Readiness check to verify all dependencies are available."""
        from app.models.database import check_db_connection
        from app.integrations.vector_store import check_vector_store_connection
        
        db_ok = await check_db_connection()
        vector_ok = await check_vector_store_connection()
        
        if db_ok and vector_ok:
            return {"status": "ready", "database": "connected", "vector_store": "connected"}
        
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "database": "connected" if db_ok else "disconnected",
                "vector_store": "connected" if vector_ok else "disconnected",
            },
        )
    
    return app


app = create_application()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8080,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
