# Migraciones de base de datos (Alembic)
Fuente de verdad: `apps/backend/alembic/`.

## Ubicación
```
apps/backend/
├── alembic.ini
└── alembic/
    ├── env.py
    ├── script.py.mako
    └── versions/
        └── 001_foundation.py
```

## Requisitos previos
- `DATABASE_URL` configurado (ver `apps/backend/app/crosscutting/config.py`).

## Comandos comunes
```bash
cd apps/backend
alembic current
alembic history --verbose
alembic upgrade head
alembic downgrade -1
```

Con Docker Compose:
```bash
pnpm db:migrate
```

## Troubleshooting
- **Síntoma:** `Target database is not up to date`.
- **Solución:** `alembic upgrade head`.

- **Síntoma:** `Can't locate revision`.
- **Solución:** `alembic history --verbose` y `alembic stamp <revision_id>`.

## Notas
- `infra/postgres/init.sql` habilita `pgvector`.
- El schema completo se aplica via Alembic (`apps/backend/alembic/`).
- Ver `docs/reference/data/postgres-schema.md` para detalle de tablas e índices.
