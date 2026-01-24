# Database Migrations (Alembic) - v6

**Project:** RAG Corp
**Last Updated:** 2026-01-22

---

## Overview

RAG Corp usa Alembic para versionar el schema PostgreSQL.
El source of truth es `apps/backend/alembic/`.

---

## Ubicacion

```
apps/backend/
├── alembic.ini
└── alembic/
    ├── env.py
    ├── script.py.mako
    └── versions/
        ├── 001_initial.py
        ├── 002_add_users.py
        ├── 003_add_document_file_metadata.py
        ├── 004_add_processing_status.py
        ├── 005_add_document_tags.py
        ├── 006_add_audit_events_and_acl.py
        ├── 007_add_workspaces_and_acl.py
        └── 008_docs_workspace_id.py
```

---

## Requisitos previos

- `DATABASE_URL` configurado
- Para `008_docs_workspace_id.py`, debe existir al menos un usuario (admin recomendado). Si no, la migracion falla con mensaje explicito.

---

## Comandos comunes

```bash
cd apps/backend
alembic current
alembic history --verbose
alembic upgrade head
alembic downgrade -1
```

Con Docker Compose (canonico):

```bash
pnpm db:migrate
```

---

## Troubleshooting

### "Target database is not up to date"

```bash
alembic current
alembic upgrade head
```

### "Can't locate revision"

```bash
alembic history --verbose
alembic stamp <revision_id>
```

### Reset destructivo (solo dev)

```bash
alembic downgrade base
alembic upgrade head
```

---

## Notas

- `infra/postgres/init.sql` solo habilita `pgvector`.
- El schema completo se aplica via Alembic.
- Ver `docs/data/postgres-schema.md` para detalle de tablas e indices.

