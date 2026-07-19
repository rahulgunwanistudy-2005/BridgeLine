"""FastAPI application factory and router wiring."""

from fastapi import FastAPI

from bridgeline.api.health import router as health_router


def create_app() -> FastAPI:
    """Build the Bridgeline API application."""

    app = FastAPI(title="Bridgeline API", version="0.1.0")
    app.include_router(health_router)
    return app


app = create_app()
