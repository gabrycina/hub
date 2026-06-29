from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from hub.bootstrap import load_config_env
from hub.config import get_settings
from hub.db import Database
from hub.routes import api, web
from hub_mcp.server import mcp as _mcp


def create_app() -> FastAPI:
    load_config_env()

    # Serve the MCP over HTTP at /mcp on the same port, so a remote agent can
    # connect with `claude mcp add --transport http hub <url>/mcp` — no local
    # install. The mounted sub-app's lifespan must be driven by the parent.
    mcp_app = _mcp.http_app(path="/")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        settings = get_settings()
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        settings.artifacts_dir.mkdir(parents=True, exist_ok=True)
        Database(settings.db_path)
        async with mcp_app.lifespan(app):
            yield

    app = FastAPI(title="Hub", version="0.1.0", lifespan=lifespan)

    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "hub"}

    app.include_router(api.router)
    app.include_router(web.router)
    app.mount("/mcp", mcp_app)
    return app


app = create_app()


def run_server() -> None:
    load_config_env()
    get_settings.cache_clear()
    settings = get_settings()
    uvicorn.run(
        "hub.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


def cli() -> None:
    from hub.cli import main

    raise SystemExit(main())


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "run":
        run_server()
    else:
        cli()