"""
===============================================================================
TARJETA CRC — app/api/main.py (Composición FastAPI / EntryPoint)
===============================================================================

Responsabilidades:
  - Crear y configurar la aplicación FastAPI (composición).
  - Registrar middlewares transversales (contexto, límites, CORS, headers).
  - Incluir routers HTTP (negocio, auth, admin) y alias de rutas.
  - Exponer endpoints operativos (/healthz, /readyz, /metrics).
  - Inicializar y cerrar recursos del proceso (pool de BD) vía lifespan.
  - Publicar el ASGI app final envuelto con rate limiting (si aplica).

Patrones aplicados:
  - Composition Root: este módulo arma el grafo de dependencias web.
  - Middleware Chain (ASGI/Starlette): concerns transversales fuera del dominio.
  - Fail-fast en startup: validación de settings + init de pool.
  - Best-effort en observabilidad: logs con request_id, sin romper el flujo.

Colaboradores:
  - crosscutting.config.get_settings
  - infrastructure.db.pool.init_pool / close_pool
  - interfaces.api.http.routes.router (router de negocio)
  - api.auth_routes / api.admin_routes (rutas auxiliares)
  - api.exception_handlers.register_exception_handlers
  - api.versioning.include_versioned_routes (alias de rutas)
===============================================================================
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Callable

from fastapi import Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from ..application.dev_seed_admin import ensure_dev_admin
from ..application.dev_seed_demo import ensure_dev_demo
from ..container import get_document_repository
from ..crosscutting.config import get_settings
from ..crosscutting.logger import logger
from ..crosscutting.middleware import BodyLimitMiddleware, RequestContextMiddleware
from ..crosscutting.rate_limit import RateLimitMiddleware
from ..crosscutting.security import SecurityHeadersMiddleware
from ..identity.auth import is_auth_enabled
from ..identity.rbac import require_metrics_permission
from ..infrastructure.db.pool import close_pool, init_pool
from ..interfaces.api.http.routes import router as business_router
from .auth_routes import router as auth_router
from .exception_handlers import register_exception_handlers
from .versioning import include_versioned_routes

# -----------------------------------------------------------------------------
# Lifespan (startup/shutdown)
# -----------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Ciclo de vida del proceso.

    - Valida settings (seguridad en producción).
    - Inicializa el pool de BD antes de que se use cualquier repositorio.
    - Ejecuta seed de desarrollo si está habilitado.
    - Cierra el pool al apagar el proceso.
    """
    settings = get_settings()

    if settings.is_production():
        settings.validate_security_requirements()

    init_pool(
        database_url=settings.database_url,
        min_size=settings.db_pool_min_size,
        max_size=settings.db_pool_max_size,
    )

    try:
        _run_dev_seed_if_enabled(settings)
        logger.info(
            "Backend iniciado",
            extra={
                "auth_enabled": is_auth_enabled(),
                "rate_limit_rps": settings.rate_limit_rps,
                "db_pool_min": settings.db_pool_min_size,
                "db_pool_max": settings.db_pool_max_size,
            },
        )
        yield
    finally:
        close_pool()
        logger.info("Backend detenido")


def _run_dev_seed_if_enabled(settings) -> None:
    """
    Ejecuta el seed (admin/demo) cuando está habilitado.

    Nota de diseño:
      - Se hace aquí (startup) para evitar "side-effects" en import-time.
      - Se usan adaptadores mínimos para no acoplar los módulos de seed a Postgres.
    """
    try:
        # R: Importes tardíos para reducir acoplamiento y tiempos de importación.
        from ..identity.auth_users import hash_password
        from ..infrastructure.repositories.postgres.user import (
            create_user as pg_create_user,
        )
        from ..infrastructure.repositories.postgres.user import (
            get_user_by_email as pg_get_user_by_email,
        )
        from ..infrastructure.repositories.postgres.user import (
            update_user as pg_update_user,
        )
        from ..infrastructure.repositories.postgres.workspace import (
            PostgresWorkspaceRepository,
        )

        class _PostgresUserRepoAdapter:
            """Adaptador mínimo (puerto requerido por dev_seed_*)."""

            def get_user_by_email(self, email: str):
                return pg_get_user_by_email(email)

            def create_user(
                self,
                *,
                email: str,
                password_hash: str,
                role,
                is_active: bool,
            ):
                return pg_create_user(
                    email=email,
                    password_hash=password_hash,
                    role=role,
                    is_active=is_active,
                )

            def update_user(
                self,
                user_id,
                *,
                password_hash=None,
                role=None,
                is_active=None,
            ):
                return pg_update_user(
                    user_id,
                    password_hash=password_hash,
                    role=role,
                    is_active=is_active,
                )

        user_repo = _PostgresUserRepoAdapter()
        workspace_repo = PostgresWorkspaceRepository()
        password_hasher: Callable[[str], str] = hash_password

        ensure_dev_admin(
            settings,
            user_repo=user_repo,
            password_hasher=password_hasher,
            env=os.environ,
        )
        ensure_dev_demo(
            settings,
            user_repo=user_repo,
            workspace_repo=workspace_repo,
            password_hasher=password_hasher,
        )

    except Exception as e:
        # R: En startup preferimos fallar rápido si el seed está habilitado
        #     y algo salió mal, para no dejar el sistema en un estado inconsistente.
        logger.error(
            "Fallo en seed de desarrollo",
            exc_info=True,
            extra={"error": str(e)},
        )
        raise


# -----------------------------------------------------------------------------
# OpenAPI: seguridad dual + ajustes de parámetros
# -----------------------------------------------------------------------------


def _custom_openapi(app: FastAPI) -> dict:
    """
    Genera un OpenAPI enriquecido con esquemas de seguridad (API Key + JWT).

    Nota:
      - No cambia la seguridad real (eso lo hacen las dependencias),
        solo mejora la documentación.
    """
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(title=app.title, version=app.version, routes=app.routes)

    components = schema.setdefault("components", {})
    security_schemes = components.setdefault("securitySchemes", {})
    security_schemes.update(
        {
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key",
                "description": "API key con los permisos adecuados.",
            },
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "JWT via Authorization: Bearer <token> o cookie httpOnly.",
            },
        }
    )

    # R: Por defecto documentamos que ambas formas son aceptables.
    dual_security = [{"ApiKeyAuth": []}, {"BearerAuth": []}]
    schema["security"] = dual_security

    settings = get_settings()
    public_paths = {"/healthz", "/readyz", "/auth/login", "/auth/logout"}
    jwt_only_paths = {"/auth/me"}

    for path, methods in schema.get("paths", {}).items():
        for operation in methods.values():
            if not isinstance(operation, dict):
                continue

            if path in public_paths:
                operation["security"] = []
                continue

            if path in jwt_only_paths:
                operation["security"] = [{"BearerAuth": []}]
                continue

            if path == "/metrics":
                operation["security"] = (
                    [{"ApiKeyAuth": []}] if settings.metrics_require_auth else []
                )
                continue

            # R: Rutas de auth/admin y rutas del negocio aceptan autenticación dual.
            if path.startswith("/auth/") or path.startswith("/admin/"):
                operation["security"] = dual_security
                continue

            if path.startswith("/v1/") or path.startswith("/api/v1/"):
                operation["security"] = dual_security
                continue

    # R: Ajuste de documentación: algunos endpoints usan workspace_id como query param
    #     pero internamente es obligatorio (validación en use case).
    workspace_id_required_exclusions = {
        "/v1/workspaces",
        "/api/v1/workspaces",
    }
    for path, methods in schema.get("paths", {}).items():
        if not (path.startswith("/v1/") or path.startswith("/api/v1/")):
            continue
        if "/workspaces/" in path or path in workspace_id_required_exclusions:
            continue
        for operation in methods.values():
            if not isinstance(operation, dict):
                continue
            for param in operation.get("parameters", []):
                if param.get("name") == "workspace_id" and param.get("in") == "query":
                    param["required"] = True

    app.openapi_schema = schema
    return schema


# -----------------------------------------------------------------------------
# Endpoints operativos
# -----------------------------------------------------------------------------


def _get_allowed_origins() -> list[str]:
    """Lee orígenes permitidos para CORS con fallback seguro (tests/import-time)."""
    try:
        return get_settings().get_allowed_origins_list()
    except Exception:
        return ["http://localhost:3000"]


def create_fastapi_app() -> FastAPI:
    """
    Crea la instancia FastAPI (sin wrapper ASGI de rate limiting).

    Separamos esto para:
      - Facilitar tests (importar fastapi_app directo).
      - Mantener el wrapper ASGI como capa externa.
    """
    app = FastAPI(
        title="RAG Corp API",
        version="0.1.0",
        lifespan=lifespan,
        openapi_tags=[
            {"name": "workspaces", "description": "Gestión de workspaces."},
            {"name": "documents", "description": "Ingesta y manejo de documentos."},
            {"name": "query", "description": "Búsqueda semántica y respuestas RAG."},
            {"name": "admin", "description": "Operaciones administrativas."},
            {
                "name": "auth",
                "description": "Autenticación de usuarios (JWT) y administración.",
            },
        ],
    )

    # R: OpenAPI enriquecido con seguridad dual.
    app.openapi = lambda: _custom_openapi(app)

    # R: Middlewares (se ejecutan en orden inverso al registro).
    app.add_middleware(BodyLimitMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestContextMiddleware)

    # R: CORS configurable por settings.
    try:
        allow_credentials = bool(get_settings().cors_allow_credentials)
    except Exception:
        allow_credentials = False

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_get_allowed_origins(),
        allow_credentials=allow_credentials,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-API-Key", "X-Request-Id"],
    )

    # R: Router de negocio bajo prefijo /v1 (convención estable del backend).
    app.include_router(business_router, prefix="/v1")

    # R: Rutas auxiliares fuera del prefijo (operaciones puntuales).
    app.include_router(auth_router)

    from .admin_routes import router as admin_router  # import tardío para evitar ciclos

    app.include_router(admin_router)

    # R: Alias de rutas (ej.: /api/v1) sin tocar los routers de negocio.
    include_versioned_routes(app)

    # R: Handlers centralizados de excepciones (RFC7807).
    register_exception_handlers(app)

    # -------------------------------------------------------------------------
    # Health / Readiness
    # -------------------------------------------------------------------------

    @app.get("/healthz", tags=["admin"])
    def healthz(request: Request, full: bool = False):
        """
        Health check ampliado.

        - Siempre chequea BD.
        - Si full=true, chequea conectividad Google API (si está habilitado).
        """
        settings = get_settings()
        db_status = "disconnected"
        try:
            repo = get_document_repository()
            if repo.ping():
                db_status = "connected"
        except Exception as e:
            logger.warning("Health check: BD no disponible", extra={"error": str(e)})

        google_status = "skipped"
        if full:
            if settings.healthcheck_google_enabled:
                google_status = _check_google_api()
            else:
                google_status = "disabled"

        return {
            "ok": db_status == "connected"
            and (google_status in {"available", "skipped", "disabled"}),
            "db": db_status,
            "google": google_status,
            "request_id": getattr(request.state, "request_id", None),
        }

    @app.get("/readyz", tags=["admin"])
    def readyz(request: Request):
        """Readiness mínimo: dependencias core (BD)."""
        db_status = "disconnected"
        try:
            repo = get_document_repository()
            if repo.ping():
                db_status = "connected"
        except Exception as e:
            logger.warning("Ready check: BD no disponible", extra={"error": str(e)})

        return {
            "ok": db_status == "connected",
            "db": db_status,
            "request_id": getattr(request.state, "request_id", None),
        }

    # -------------------------------------------------------------------------
    # Metrics
    # -------------------------------------------------------------------------

    @app.get("/metrics", tags=["admin"])
    def metrics(_auth: None = Depends(require_metrics_permission())):
        """Expone métricas Prometheus (si está instalado)."""
        from ..crosscutting.metrics import get_metrics_response, is_prometheus_available

        if not is_prometheus_available():
            return Response(
                content="# prometheus_client no instalado\n",
                media_type="text/plain",
            )

        body, content_type = get_metrics_response()
        return Response(content=body, media_type=content_type)

    return app


def _check_google_api() -> str:
    """
    Verifica conectividad con Google API mediante una llamada mínima de embeddings.

    Retorna:
      - "available" | "unavailable" | "disabled"
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return "disabled"

    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        resp = client.models.embed_content(
            model="text-embedding-004",
            contents=["health check"],
            config={"task_type": "retrieval_query"},
        )
        embeddings = resp.embeddings or []
        if embeddings and embeddings[0].values:
            return "available"
        return "unavailable"
    except Exception as e:
        logger.warning(
            "Health check: Google API no disponible", extra={"error": str(e)}
        )
        return "unavailable"


# -----------------------------------------------------------------------------
# Export público: `app` (ASGI) + `fastapi_app` (FastAPI para tests)
# -----------------------------------------------------------------------------

fastapi_app = create_fastapi_app()

# R: Wrapper ASGI para rate limiting. Si está deshabilitado en settings, pasa-through.
app = RateLimitMiddleware(fastapi_app)

__all__ = ["app", "fastapi_app"]
