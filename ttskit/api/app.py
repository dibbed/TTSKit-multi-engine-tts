"""
FastAPI REST API for TTSKit.

This module creates and configures the main FastAPI application
with all necessary middleware, routers, and exception handlers.
"""

import time

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..utils.logging_config import get_logger
from ..version import __version__
from .middleware import setup_all_middleware
from .routers import admin_router, engines_router, synthesis_router, system_router

logger = get_logger(__name__)

start_time = time.time()


class HealthResponse(BaseModel):
    """Model for API health check responses.

    This model defines the structure of health check responses,
    including service status, engine availability, and uptime information.

    Attributes:
        status (str): Service status (healthy/unhealthy).
        engines (int): Number of available engines.
        uptime (float): Service uptime in seconds.
        version (str): TTSKit version.
    """

    status: str = Field(description="Service status")
    engines: int = Field(description="Number of available engines")
    uptime: float = Field(description="Service uptime in seconds")
    version: str = Field(description="TTSKit version")


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.

    Returns:
        Fully configured FastAPI application with middleware, routers, and handlers
    """
    app = FastAPI(
        title="TTSKit API",
        description="Professional Text-to-Speech API with multiple engines",
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        openapi_tags=[
            {"name": "synthesis", "description": "Text-to-Speech synthesis endpoints"},
            {"name": "engines", "description": "TTS engines and voices management"},
            {"name": "system", "description": "System information and monitoring"},
            {
                "name": "admin",
                "description": "Administrative functions and API key management",
            },
        ],
    )

    from fastapi.openapi.utils import get_openapi

    def custom_openapi():
        """
        Custom OpenAPI schema generator with authentication components.

        Returns:
            dict: The modified OpenAPI schema with security definitions.
        """
        if app.openapi_schema:
            return app.openapi_schema

        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )

        openapi_schema["components"]["securitySchemes"] = {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "API Key",
                "description": "Enter your API key in the format: Bearer <your-api-key>",
            }
        }

        for path_item in openapi_schema["paths"].values():
            for operation in path_item.values():
                if isinstance(operation, dict) and "tags" in operation:
                    if operation["tags"] and operation["tags"][0] in [
                        "system",
                        "admin",
                    ]:
                        operation["security"] = [{"BearerAuth": []}]
                    elif operation["tags"] and operation["tags"][0] in [
                        "synthesis",
                        "engines",
                    ]:
                        if "security" in operation and operation["security"]:
                            for security_item in operation["security"]:
                                if "HTTPBearer" in security_item:
                                    security_item["BearerAuth"] = security_item.pop(
                                        "HTTPBearer"
                                    )

        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi

    setup_all_middleware(app)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        """Return 422 status code for Pydantic validation errors.

        Args:
            request (Request): The incoming HTTP request.
            exc (RequestValidationError): The Pydantic validation exception.

        Returns:
            JSONResponse: Response with validation error details.
        """
        return JSONResponse(
            status_code=422,
            content={"detail": f"Validation error: {exc.errors()}"},
            headers={"X-Error-Type": "validation_error"},
        )

    @app.get("/", response_model=dict[str, str])
    async def root():
        """Get basic service information and API endpoints.

        Returns:
            dict[str, str]: Dictionary containing service details and API endpoints.
        """
        return {
            "service": "TTSKit API",
            "version": __version__,
            "status": "running",
            "docs": "/docs",
            "api": "/api/v1",
        }

    @app.get("/health", response_model=HealthResponse)
    async def health():
        """Provide public health check endpoint.

        Returns:
            HealthResponse: Health status with engine availability and uptime.
        """
        try:
            from ..public import get_engines

            engines = get_engines()
            available_engines = [e for e in engines if e.get("available", False)]

            return HealthResponse(
                status="healthy",
                engines=len(available_engines),
                uptime=time.time() - start_time,
                version=__version__,
            )
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return HealthResponse(
                status="unhealthy",
                engines=0,
                uptime=time.time() - start_time,
                version=__version__,
            )

    app.include_router(synthesis_router)
    app.include_router(engines_router)
    app.include_router(system_router)
    app.include_router(admin_router)

    return app


app = create_app()
