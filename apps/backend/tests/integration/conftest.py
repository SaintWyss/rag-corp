"""
Name: Integration Test DB Setup

Responsibilities:
  - Ensure database schema exists before integration tests run
  - Run Alembic migrations once per test session

Notes:
  - Only runs when RUN_INTEGRATION=1
  - Uses DATABASE_URL from environment (see alembic/env.py)
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Optional, Tuple

import pytest
from alembic import command
from alembic.config import Config
from app.crosscutting.config import get_settings
from app.infrastructure.db.pool import close_pool, init_pool
from psycopg import connect

DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_HOST_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "rag")
DEFAULT_DATABASE_URL = (
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)


def _pgvector_available(url: str) -> Tuple[bool, Optional[Exception]]:
    try:
        with connect(url, autocommit=True, connect_timeout=2) as conn:
            row = conn.execute(
                "SELECT 1 FROM pg_available_extensions WHERE name = 'vector'"
            ).fetchone()
            if row is None:
                return False, RuntimeError(
                    "pgvector extension is not available on this server"
                )
        return True, None
    except Exception as exc:
        return False, exc


def _docker_db_url() -> Optional[str]:
    repo_root = Path(__file__).resolve().parents[4]
    compose_path = repo_root / "compose.yaml"
    try:
        result = subprocess.run(
            ["docker", "compose", "-f", str(compose_path), "ps", "-q", "db"],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return None

    container_id = result.stdout.strip()
    if not container_id:
        return None

    try:
        inspect = subprocess.run(
            [
                "docker",
                "inspect",
                "-f",
                "{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}",
                container_id,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return None

    ip = inspect.stdout.strip()
    if not ip:
        return None

    return f"postgresql://postgres:postgres@{ip}:5432/rag"


def _resolve_database_url() -> str:
    explicit_url = os.getenv("DATABASE_URL")
    if explicit_url and explicit_url != DEFAULT_DATABASE_URL:
        ok, exc = _pgvector_available(explicit_url)
        if ok:
            return explicit_url
        raise RuntimeError(
            "DATABASE_URL points to a server without pgvector. "
            "Set DATABASE_URL to a pgvector-enabled Postgres instance."
        ) from exc

    ok, exc = _pgvector_available(DEFAULT_DATABASE_URL)
    if ok:
        return DEFAULT_DATABASE_URL

    docker_url = _docker_db_url()
    if docker_url:
        ok, docker_exc = _pgvector_available(docker_url)
        if ok:
            return docker_url
        raise RuntimeError(
            "Docker DB found but pgvector is not available in that container."
        ) from docker_exc

    raise RuntimeError(
        "pgvector is required for integration tests. "
        "Start the compose DB or install pgvector on your Postgres server."
    ) from exc


if os.getenv("RUN_INTEGRATION") == "1":
    os.environ["APP_ENV"] = "integration"
    get_settings.cache_clear()
    os.environ["DATABASE_URL"] = _resolve_database_url()


def pytest_configure(config) -> None:
    if os.getenv("RUN_INTEGRATION") == "1" and hasattr(config.option, "cov_fail_under"):
        config.option.cov_fail_under = 0
        cov_plugin = config.pluginmanager.getplugin("cov") or config.pluginmanager.getplugin(
            "_cov"
        )
        if cov_plugin is not None:
            if hasattr(cov_plugin, "cov_fail_under"):
                cov_plugin.cov_fail_under = 0
            if hasattr(cov_plugin, "options") and hasattr(
                cov_plugin.options, "cov_fail_under"
            ):
                cov_plugin.options.cov_fail_under = 0


@pytest.fixture(scope="session", autouse=True)
def apply_migrations() -> None:
    """Run Alembic migrations for integration tests."""
    if os.getenv("RUN_INTEGRATION") != "1":
        return

    database_url = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    try:
        with connect(database_url, autocommit=True) as conn:
            conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    except Exception as exc:
        raise RuntimeError(
            "pgvector is required for integration tests. "
            "Use the docker compose DB (pgvector/pgvector image) or install the "
            "pgvector extension on your Postgres server."
        ) from exc

    backend_dir = Path(__file__).resolve().parents[2]
    config_path = backend_dir / "alembic.ini"
    alembic_dir = backend_dir / "alembic"

    config = Config(str(config_path))
    config.set_main_option("script_location", str(alembic_dir))

    command.upgrade(config, "head")


@pytest.fixture(scope="session", autouse=True)
def init_db_pool(apply_migrations) -> None:
    if os.getenv("RUN_INTEGRATION") != "1":
        return

    settings = get_settings()
    init_pool(
        database_url=settings.database_url,
        min_size=settings.db_pool_min_size,
        max_size=settings.db_pool_max_size,
    )
    yield
    close_pool()
