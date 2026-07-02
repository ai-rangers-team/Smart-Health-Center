import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.config import settings
from app.routers import ai

limiter = Limiter(key_func=get_remote_address)


def create_app() -> FastAPI:
    app = FastAPI(title="Smart Health API")
    app.state.limiter = limiter
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.allowed_origin],
        allow_methods=["*"], allow_headers=["*"], allow_credentials=True,
    )

    @app.get("/health")
    def health():
        return {"status": "ok"}

    # API routers MUST be registered before the catch-all static mount below,
    # otherwise StaticFiles at "/" shadows every /api/* route and returns 404.
    app.include_router(ai.router)

    if os.path.isdir("static"):
        app.mount("/", StaticFiles(directory="static", html=True), name="static")

    return app


app = create_app()
