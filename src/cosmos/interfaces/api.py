"""FastAPI-based HTTP API for CosmOS.

Endpoints:
  POST   /api/v1/tasks             — создать задачу
  GET    /api/v1/tasks             — список задач
  GET    /api/v1/tasks/{id}        — детали задачи
  POST   /api/v1/tasks/{id}/cancel — отмена задачи
  GET    /api/v1/agents            — список агентов
  GET    /api/v1/doctor            — диагностика
  POST   /api/v1/memory/search     — поиск по памяти
  GET    /api/v1/health            — healthcheck (без auth)
  GET    /api/v1/version           — версия (без auth)

Authentication: Bearer token (API key) on all endpoints except /health and /version.
"""

import logging
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request
from starlette.responses import FileResponse
from pydantic import BaseModel

from ..config import CosmOSConfig
from ..core.state import TaskStore
from ..core.router import TaskRouter

logger = logging.getLogger(__name__)

security_scheme = HTTPBearer(auto_error=False)


# ── Request / Response models ─────────────────────────


class TaskCreateRequest(BaseModel):
    description: str
    agent: Optional[str] = None
    host: Optional[str] = None
    workdir: Optional[str] = None
    path: Optional[str] = None


class MemorySearchRequest(BaseModel):
    query: str
    source: str = "all"
    limit: int = 10


# ── FastAPI application factory ────────────────────────


def create_app(config: CosmOSConfig,
               router: TaskRouter,
               store: TaskStore) -> FastAPI:
    """Create the FastAPI application wired to CosmOS Core."""

    api_config = config.interfaces.api
    app = FastAPI(
        title="CosmOS API",
        version=config.version,
        description=f"{config.name} — API для управления задачами и агентами",
    )

    # ── Auth middleware ─────────────────────────────────

    async def verify_api_key(
        credentials: Optional[HTTPAuthorizationCredentials] = Security(security_scheme),
    ) -> str:
        """Verify Bearer token matches COSMOS_API_KEY."""
        if not api_config.api_key:
            # API key not configured → allow all (dev mode)
            return "dev"
        if credentials is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing Authorization header",
            )
        if credentials.credentials != api_config.api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
            )
        return credentials.credentials

    # ── GET routes (no auth — read-only, safe for LAN) ─

    @app.get("/api/v1/health", tags=["System"])
    async def health():
        """Health check — no auth required."""
        return {"status": "ok", "version": config.version}

    @app.get("/api/v1/version", tags=["System"])
    async def version():
        """Version info — no auth required."""
        return {
            "name": config.name,
            "version": config.version,
            "agents": len(router.list_agents()),
            "remote_hosts": len(config.remote_hosts),
        }

    @app.get("/api/v1/tasks", tags=["Tasks"])
    async def list_tasks(
        limit: int = 10,
        status_filter: Optional[str] = None,
    ):
        """List recent tasks (optionally filtered by status)."""
        tasks = store.list_tasks(limit=limit)
        if status_filter:
            tasks = [t for t in tasks if t.get("status") == status_filter]
        return {"tasks": tasks, "count": len(tasks)}

    @app.get("/api/v1/tasks/{task_id}", tags=["Tasks"])
    async def get_task(
        task_id: str,
    ):
        """Get task details by ID."""
        task = store.get_task(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found",
            )
        return task

    @app.get("/api/v1/agents", tags=["Agents"])
    async def list_agents():
        """List all registered agents with availability and capabilities."""
        agents = router.list_agents()
        result = []
        for a in agents:
            result.append({
                "name": a.name,
                "command": a.command,
                "available": a.available,
                "capabilities": sorted(c.value for c in a.capabilities),
                "description": a.description,
            })
        return {"agents": result, "count": len(result)}

    @app.get("/api/v1/doctor", tags=["System"])
    async def doctor():
        """Run diagnostics — uses cached agent info."""
        checks = {
            "config": f"{config.name} v{config.version}",
            "task_store": "ok",
            "agents_available": 0,
            "agents_total": 0,
            "remote_hosts": len(config.remote_hosts),
        }
        try:
            store.health()
            checks["task_store"] = "ok"
        except Exception:
            checks["task_store"] = "error"

        agents = router.list_agents()
        checks["agents_total"] = len(agents)
        checks["agents_available"] = len([a for a in agents if a.available])

        return {
            "status": "ok" if checks["task_store"] == "ok" else "degraded",
            "checks": checks,
        }

    # ── POST routes (require auth) ─────────────────────

    @app.post("/api/v1/tasks", tags=["Tasks"])
    async def create_task(
        req: TaskCreateRequest,
        api_key: str = Security(verify_api_key),
    ):
        """Create and execute a task."""
        task = router.run_task(
            description=req.description,
            agent_name=req.agent,
            host=req.host,
            workdir=req.workdir,
            path=req.path,
        )
        return task

    @app.post("/api/v1/tasks/{task_id}/cancel", tags=["Tasks"])
    async def cancel_task(
        task_id: str,
        api_key: str = Security(verify_api_key),
    ):
        """Cancel a running task (supported for remote tasks only)."""
        task = store.get_task(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found",
            )

        meta = task.get("metadata", {}) or {}
        if not meta.get("remote"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cancel supported only for remote tasks",
            )

        remote_task_id = meta.get("remote_task_id")
        host_name = meta.get("remote_host")
        if not remote_task_id or not host_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Remote task metadata incomplete",
            )

        # Find the remote agent and cancel
        for name, agent in router.remote_agents.items():
            if agent.host_name == host_name:
                err = agent.cancel_task(remote_task_id)
                store.update_task(task_id, status="cancelled")
                detail = err or "Cancelled successfully"
                return {"task_id": task_id, "status": "cancelled", "detail": detail}

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No remote agent found for host {host_name}",
        )

    @app.post("/api/v1/memory/search", tags=["Memory"])
    async def memory_search(
        req: MemorySearchRequest,
        api_key: str = Security(verify_api_key),
    ):
        """Search across memory backends."""
        from ..memory import MemoryItem
        from ..memory.sqlite_memory import SQLiteMemory
        from ..memory.obsidian_memory import ObsidianMemory

        memory_cfg = config.memory
        results: list[dict] = []

        if memory_cfg.sqlite.enabled and req.source in ("all", "sqlite"):
            sqlite_path = memory_cfg.sqlite.path
            if not sqlite_path.startswith("/"):
                root = Path(config.root)
                sqlite_path = str(root / sqlite_path)
            sqlite = SQLiteMemory(sqlite_path)
            for item in sqlite.search(req.query, limit=req.limit):
                results.append({
                    "key": item.key,
                    "content": item.content[:500],
                    "source": "sqlite",
                    "tags": item.tags,
                    "score": item.score,
                })

        if memory_cfg.obsidian.enabled and req.source in ("all", "obsidian"):
            obsidian = ObsidianMemory(
                vault_path=memory_cfg.obsidian.vault_path,
                notes_folder=memory_cfg.obsidian.notes_folder,
            )
            for item in obsidian.search(req.query, limit=req.limit):
                results.append({
                    "key": item.key,
                    "content": item.content[:500],
                    "source": "obsidian",
                    "tags": item.tags,
                    "score": item.score,
                })

        return {"results": results[:req.limit], "count": min(len(results), req.limit)}

    # ── Serve SPA (built UI) ────────────────────────────
    ui_dir = Path(__file__).resolve().parent.parent.parent.parent / "ui" / "dist"
    if ui_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(ui_dir / "assets")), name="cosmos_assets")

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str, request: Request):
            # Only handle non-API routes
            if full_path.startswith("api/"):
                from fastapi.responses import JSONResponse
                return JSONResponse({"detail": "Not Found"}, status_code=404)
            index_path = ui_dir / "index.html"
            if index_path.exists():
                return FileResponse(str(index_path))
            return {"error": "UI not built"}
    else:
        logger.info("UI not built — run 'npm run build' in ui/ to enable the web interface")

    return app


# ── CLI entry point: 'cosmos api' ──────────────────────


def run_api(config: CosmOSConfig, router: TaskRouter, store: TaskStore):
    """Run the API server (blocking)."""
    api_config = config.interfaces.api
    app = create_app(config, router, store)

    if not api_config.api_key:
        logger.warning("COSMOS_API_KEY не задан — API работает без аутентификации!")

    logger.info(
        "Starting API on %s:%s",
        api_config.host,
        api_config.port,
    )
    log_level = logging.getLevelName(logger.level).lower()
    # uvicorn doesn't accept 'notset' — default to 'info'
    if log_level == "notset":
        log_level = "info"
    uvicorn.run(
        app,
        host=api_config.host,
        port=api_config.port,
        log_level=log_level,
    )
