"""FastAPI application entrypoint."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agentbot.api.routes.browser import router as browser_router
from agentbot.api.routes.conversations import router as conversations_router
from agentbot.api.routes.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(title="AgentBot Local API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(browser_router)
    app.include_router(health_router)
    app.include_router(conversations_router)
    return app


app = create_app()
