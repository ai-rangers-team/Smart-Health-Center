import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from app.config import settings
from app.routers import ai, alerts, centres, dashboard, operator, seed

# 60 req/min per client IP across the API — enough for normal dashboard use,
# blocks abuse of the Gemini-backed endpoints.
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])


def create_app() -> FastAPI:
    app = FastAPI(title="Smart Health API")
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
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
    app.include_router(centres.router)
    app.include_router(operator.router)
    app.include_router(dashboard.router)
    app.include_router(alerts.router)
    app.include_router(ai.router)
    app.include_router(ai.recs_router)
    app.include_router(seed.router)

    if os.path.isdir("static"):
        app.mount("/", StaticFiles(directory="static", html=True), name="static")

    return app


app = create_app()
