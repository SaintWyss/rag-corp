"""
============================================================
TARJETA CRC — infrastructure/repositories/postgres_user_repo.py
============================================================
Class: PostgresUserRepository

Responsibilities:
  - Cargar usuarios para autenticación (por email / por id).
  - Crear usuarios y actualizar campos administrables (password, role, is_active).
  - Ejecutar SQL parametrizado contra la tabla `users` (contrato con migraciones).
  - Mapear filas crudas -> entidad de dominio `User` y validar `UserRole`.
  - Exponer fallos consistentes vía `DatabaseError` con logging estructurado.
  - Mantener caminos de lectura enfocados (auth) y respuestas determinísticas.

Collaborators:
  - psycopg_pool.ConnectionPool (pool de conexiones)
  - infrastructure.db.pool.get_pool (factory/accesor del pool global)
  - identity.users.User / UserRole (modelo de dominio)
  - crosscutting.logger.logger (logs)
  - crosscutting.exceptions.DatabaseError (error estándar de infraestructura)

Constraints / Notes (Clean Code / SOLID):
  - Repositorio puro: NO define reglas de negocio (política de roles, etc.).
  - Retorna None cuando no existe el recurso (no exception por “not found”).
  - Validación de roles: si el valor persistido no corresponde a UserRole -> DatabaseError.
  - SQL parametrizado siempre (nunca interpolar input de usuario).
  - Evitar duplicación: helper de SELECT + helper de mapping + errores consistentes.
  - Orden estable en listados: created_at DESC, id DESC.
============================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional
from uuid import UUID, uuid4

from psycopg_pool import ConnectionPool

from ....crosscutting.exceptions import DatabaseError
from ....crosscutting.logger import logger
from ....identity.users import User, UserRole

# ============================================================
# Constantes y contratos de SQL
# ============================================================
# R: Lista explícita de columnas para mantener el contrato estable con migraciones.
#    Si el esquema cambia, este string te obliga a ajustar TODO en un solo lugar.
_USER_COLUMNS = "id, email, password_hash, role, is_active, created_at"

# R: Ordering determinístico. Si created_at empata, id ordena estable.
_USER_ORDER_BY = "created_at DESC, id DESC"


# ============================================================
# Acceso al pool (Dependency Injection friendly)
# ============================================================
def _get_pool() -> ConnectionPool:
    """
    Obtiene el pool global.

    Nota: En repositorios más “OO” esto se inyecta por __init__ (mejor testability).
    Acá mantenemos el estilo funcional que ya usás, pero con helpers DRY.
    """
    from ..db.pool import get_pool

    return get_pool()


# ============================================================
# Helpers internos: mapping + ejecución
# ============================================================
def _row_to_user(row: tuple) -> User:
    """
    Convierte una fila de `users` a entidad de dominio `User`.

    Política:
    - Role casting debe ser estricto: si el valor no matchea el enum -> DatabaseError.
      Esto te protege contra “drift” del esquema o datos inválidos.
    """
    try:
        role = UserRole(row[3])
    except ValueError as exc:
        raise DatabaseError(f"Invalid user role in database: {row[3]}") from exc

    return User(
        id=row[0],
        email=row[1],
        password_hash=row[2],
        role=role,
        is_active=row[4],
        created_at=row[5],
    )


def _fetchone(
    *,
    query: str,
    params: Iterable[object],
    log_msg: str,
    log_extra: dict[str, object],
) -> tuple | None:
    """
    Ejecuta un SELECT ... fetchone() con manejo consistente de errores.

    - Centraliza logging + raise DatabaseError.
    - Usa tuple(params) por consistencia con psycopg.
    """
    try:
        pool = _get_pool()
        with pool.connection() as conn:
            return conn.execute(query, tuple(params)).fetchone()
    except Exception as exc:
        logger.exception(log_msg, extra={**log_extra, "error": str(exc)})
        raise DatabaseError(f"{log_msg}: {exc}") from exc


def _fetchall(
    *,
    query: str,
    params: Iterable[object] = (),
    log_msg: str,
    log_extra: dict[str, object],
) -> list[tuple]:
    """Ejecuta un SELECT ... fetchall() con manejo consistente de errores."""
    try:
        pool = _get_pool()
        with pool.connection() as conn:
            return conn.execute(query, tuple(params)).fetchall()
    except Exception as exc:
        logger.exception(log_msg, extra={**log_extra, "error": str(exc)})
        raise DatabaseError(f"{log_msg}: {exc}") from exc


# ============================================================
# API del repositorio (funcional, coherente con tu base)
# ============================================================
def get_user_by_email(email: str) -> Optional[User]:
    """
    Obtiene un usuario por email (autenticación).

    Decisiones:
    - No normalizamos el email acá (lower/trim) porque eso es política.
      Si querés “case-insensitive auth”, lo correcto es:
        - normalizar al persistir (email lower)
        - y/o índice/constraint funcional (lower(email))
      (ver sección de mejoras al final).
    """
    row = _fetchone(
        query=f"""
            SELECT {_USER_COLUMNS}
            FROM users
            WHERE email = %s
        """,
        params=(email,),
        log_msg="PostgresUserRepository: get_user_by_email failed",
        log_extra={"email": email},
    )
    return _row_to_user(row) if row else None


def get_user_by_id(user_id: UUID) -> Optional[User]:
    """
    Obtiene un usuario por ID (validación de token / sesión).
    """
    row = _fetchone(
        query=f"""
            SELECT {_USER_COLUMNS}
            FROM users
            WHERE id = %s
        """,
        params=(user_id,),
        log_msg="PostgresUserRepository: get_user_by_id failed",
        log_extra={"user_id": str(user_id)},
    )
    return _row_to_user(row) if row else None


def list_users(*, limit: int = 200, offset: int = 0) -> list[User]:
    """
    Lista usuarios (herramienta admin).

    Guard rails:
    - limit <= 0 => []
    - offset < 0 => 0
    """
    if limit <= 0:
        return []
    if offset < 0:
        offset = 0

    rows = _fetchall(
        query=f"""
            SELECT {_USER_COLUMNS}
            FROM users
            ORDER BY {_USER_ORDER_BY}
            LIMIT %s OFFSET %s
        """,
        params=(limit, offset),
        log_msg="PostgresUserRepository: list_users failed",
        log_extra={"limit": limit, "offset": offset},
    )
    return [_row_to_user(r) for r in rows]


def create_user(
    *,
    email: str,
    password_hash: str,
    role: UserRole,
    is_active: bool = True,
) -> User:
    """
    Crea un usuario y devuelve el registro.

    Nota:
    - Si el email ya existe, Postgres va a lanzar error por uq_users_email.
      Ese error se envuelve en DatabaseError (la capa superior decide cómo responder).
    """
    user_id = uuid4()

    row = _fetchone(
        query=f"""
            INSERT INTO users (id, email, password_hash, role, is_active)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING {_USER_COLUMNS}
        """,
        params=(user_id, email, password_hash, role.value, is_active),
        log_msg="PostgresUserRepository: create_user failed",
        log_extra={"user_id": str(user_id), "email": email, "role": role.value},
    )

    if not row:
        # En INSERT ... RETURNING esto sería muy raro, pero lo dejamos explícito.
        raise DatabaseError(
            "PostgresUserRepository: create_user failed (no row returned)"
        )

    return _row_to_user(row)


def set_user_active(user_id: UUID, is_active: bool) -> Optional[User]:
    """
    Activa/desactiva usuario (admin).

    Retorna:
    - User actualizado si existía
    - None si no existía
    """
    row = _fetchone(
        query=f"""
            UPDATE users
            SET is_active = %s
            WHERE id = %s
            RETURNING {_USER_COLUMNS}
        """,
        params=(is_active, user_id),
        log_msg="PostgresUserRepository: set_user_active failed",
        log_extra={"user_id": str(user_id), "is_active": is_active},
    )
    return _row_to_user(row) if row else None


def update_user_password(user_id: UUID, password_hash: str) -> Optional[User]:
    """
    Actualiza password_hash.

    Retorna:
    - User actualizado si existía
    - None si no existía
    """
    row = _fetchone(
        query=f"""
            UPDATE users
            SET password_hash = %s
            WHERE id = %s
            RETURNING {_USER_COLUMNS}
        """,
        params=(password_hash, user_id),
        log_msg="PostgresUserRepository: update_user_password failed",
        log_extra={"user_id": str(user_id)},
    )
    return _row_to_user(row) if row else None


def update_user(
    user_id: UUID,
    *,
    password_hash: str | None = None,
    role: UserRole | None = None,
    is_active: bool | None = None,
) -> Optional[User]:
    """
    Update dinámico (admin/dev tools).

    Implementación:
    - Construye SET con los campos presentes.
    - Si no hay cambios => retorna el usuario actual (si existe).
    - Mantiene SQL parametrizado.
    """
    updates: list[str] = []
    params: list[object] = []

    if password_hash is not None:
        updates.append("password_hash = %s")
        params.append(password_hash)

    if role is not None:
        updates.append("role = %s")
        params.append(role.value)

    if is_active is not None:
        updates.append("is_active = %s")
        params.append(is_active)

    if not updates:
        # No hay cambios: devolvemos estado actual (contrato cómodo para caller).
        return get_user_by_id(user_id)

    # Importante: el id siempre al final para mantener orden mental.
    params.append(user_id)

    # updates es controlado por código (no input usuario), así que el f-string es seguro.
    query = f"""
        UPDATE users
        SET {", ".join(updates)}
        WHERE id = %s
        RETURNING {_USER_COLUMNS}
    """

    row = _fetchone(
        query=query,
        params=params,
        log_msg="PostgresUserRepository: update_user failed",
        log_extra={"user_id": str(user_id), "updates": updates},
    )
    return _row_to_user(row) if row else None


# ============================================================
# Clase wrapper (para consistencia con otros repositorios)
# ============================================================
class PostgresUserRepository:
    """
    Wrapper OO sobre las funciones del módulo.

    Por qué existe:
    - Consistencia: los demás repos son clases (PostgresDocumentRepository, etc.)
    - Inyección: permite pasar un pool custom en tests.
    - Compatibilidad: el resto del código espera importar PostgresUserRepository.

    Internamente delega a las funciones del módulo para evitar duplicación.
    """

    def __init__(self, pool: ConnectionPool | None = None) -> None:
        # Pool inyectable (para tests); si es None se usa el global.
        self._pool = pool

    # --- Lectura ---
    def get_user_by_email(self, email: str) -> Optional[User]:
        return get_user_by_email(email)

    def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        return get_user_by_id(user_id)

    def list_users(self, *, limit: int = 200, offset: int = 0) -> list[User]:
        return list_users(limit=limit, offset=offset)

    # --- Escritura ---
    def create_user(
        self,
        *,
        email: str,
        password_hash: str,
        role: UserRole,
        is_active: bool = True,
    ) -> User:
        return create_user(
            email=email,
            password_hash=password_hash,
            role=role,
            is_active=is_active,
        )

    def set_user_active(self, user_id: UUID, is_active: bool) -> Optional[User]:
        return set_user_active(user_id, is_active)

    def update_user_password(self, user_id: UUID, password_hash: str) -> Optional[User]:
        return update_user_password(user_id, password_hash)

    def update_user(
        self,
        user_id: UUID,
        *,
        password_hash: str | None = None,
        role: UserRole | None = None,
        is_active: bool | None = None,
    ) -> Optional[User]:
        return update_user(
            user_id,
            password_hash=password_hash,
            role=role,
            is_active=is_active,
        )
