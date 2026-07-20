import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.config import settings
from app.routers import ai, alerts, centres, dashboard, operator, public, seed, sms

# 60 req/min per client IP across the API — enough for normal dashboard use,
# blocks abuse of the Gemini-backed endpoints.
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])


class SPAStaticFiles(StaticFiles):
    """Serve the built SPA and fall back to index.html for client-side routes.

    Plain StaticFiles 404s any path that isn't a real file, so deep links like
    /p/{id}, /centre/{id} or /sms-demo (and a browser refresh on them) would break.
    Here a 404 on a non-/api, non-asset path returns index.html so the React router
    can take over. Genuine /api 404s stay JSON."""

    async def get_response(self, path, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404 and not path.startswith("api/"):
                return await super().get_response("index.html", scope)
            raise


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
    app.include_router(public.router)
    app.include_router(sms.router)
    app.include_router(seed.router)

    if os.path.isdir("static"):
        app.mount("/", SPAStaticFiles(directory="static", html=True), name="static")

    return app


app = create_app()
