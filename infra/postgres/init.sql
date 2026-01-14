/*
 * Name: PostgreSQL Bootstrap (pgvector)
 *
 * Responsibilities:
 *   - Enable pgvector extension for vector operations
 *   - Keep DDL minimal to avoid drift with Alembic migrations
 *
 * Notes:
 *   - Schema and indexes are managed by Alembic
 *   - IF NOT EXISTS allows re-running script without errors
 */

-- R: Enable pgvector extension for vector operations
CREATE EXTENSION IF NOT EXISTS vector;
