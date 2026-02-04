# Migrations Policy – RAG Corp

## Baseline

- **Foundation** (`001_foundation.py`) is the canonical baseline.
- It creates the complete schema from scratch.
- Downgrade is blocked by policy (`NotImplementedError`).

## Rules for Future Migrations

1. **One PR = One Migration**. Each pull request that touches the schema must include exactly one migration file.
2. **Naming**: `NNN_descriptive_name.py` (e.g., `002_add_user_avatar.py`).
3. **Constraint Naming Convention**:
   - `pk_<table>` – Primary keys
   - `uq_<table>_<col>` – Unique constraints
   - `ix_<table>_<col>` – Indexes
   - `fk_<table>_<col>__<ref_table>` – Foreign keys
4. **Never modify an applied migration**. Once merged to `main`, a migration is immutable.
5. **Downgrade**: Provide a working `downgrade()` unless explicitly blocked (like the baseline).
6. **Test locally**: Run `pnpm stack:reset && pnpm stack:core` before pushing.

## Resetting the Database

```bash
pnpm stack:reset    # Drops volumes and containers
pnpm stack:core     # Recreates from scratch with fresh migration
```
