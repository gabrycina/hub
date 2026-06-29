from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from hub.config import get_settings
from hub.db import Database
from hub.routes import api, web


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.artifacts_dir.mkdir(parents=True, exist_ok=True)
    Database(settings.db_path)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Hub", version="0.1.0", lifespan=lifespan)

    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(api.router)
    app.include_router(web.router)
    return app


app = create_app()


def cli() -> None:
    settings = get_settings()
    uvicorn.run(
        "hub.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    cli()