"""${message}

============================================================
TARJETA CRC (Class / Responsibilities / Collaborators)
============================================================
Class: ${message} (Alembic Migration)

Responsibilities:
  - Definir cambio de esquema incremental (migración atómica).
  - Mantener el esquema consistente con el contrato de datos del sistema.
  - Minimizar complejidad accidental: cambios pequeños, reversibles si aplica.

Collaborators:
  - Alembic (op)
  - SQLAlchemy (sa)
  - PostgreSQL (DDL)
  - Esquema actual (baseline + migraciones previas)

Policy:
  - 1 PR = 1 migración.
  - Nombres explícitos para constraints/índices cuando aplique.
  - Evitar migraciones “gigantes”; preferir pasos pequeños.
  - Downgrade:
      * Por defecto NO soportado (evita pérdida de datos accidental).
      * Si el cambio es 100% reversible, implementar downgrade explícito.

============================================================
Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
============================================================
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# ------------------------------------------------------------
# Alembic identifiers
# ------------------------------------------------------------
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    """
    Upgrade:
    - Aplicar cambios de esquema.
    - Mantener el cambio lo más atómico posible.
    """
% if upgrades:
${upgrades}
% else:
    pass
% endif


def downgrade() -> None:
    """
    Downgrade:
    Por política, NO se soporta downgrade por defecto.
    Implementar solo si el cambio es claramente reversible
    y no implica pérdida de datos.
    """
% if downgrades:
${downgrades}
% else:
    raise NotImplementedError(
        "Downgrade no soportado por política. "
        "Si se requiere rollback, crear una migración correctiva nueva."
    )
% endif