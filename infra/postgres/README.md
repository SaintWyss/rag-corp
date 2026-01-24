# infra/postgres/ — README

> **Navegación:** [← Volver a infra/](../README.md) · [← Volver a raíz](../../README.md)

## TL;DR (30 segundos)

- **Qué es:** Script de inicialización de PostgreSQL.
- **Para qué sirve:** Habilitar la extensión `pgvector` que permite búsqueda vectorial (necesaria para RAG).
- **Quién la usa:** Docker Compose al levantar el contenedor `db`.
- **Impacto si se borra:** El backend fallará con "extension vector does not exist" — **crítico**.

---

## Para alguien con 0 conocimientos

### ¿Qué problema resuelve?

RAG Corp usa "embeddings" (representaciones numéricas de texto) para encontrar documentos relevantes. PostgreSQL no sabe hacer esto por defecto. La extensión `pgvector` le enseña a PostgreSQL a guardar y buscar estos vectores.

Este script se ejecuta **automáticamente** la primera vez que se crea la base de datos, habilitando esa capacidad.

**Analogía:** Es como instalar un plugin en tu navegador antes de poder usar una funcionalidad especial.

### ¿Qué hay acá adentro?

```
postgres/
└── init.sql    # Único archivo: habilita pgvector
```

**Contenido de `init.sql`:**
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### ¿Cómo se usa paso a paso?

**No necesitás hacer nada manualmente.** Docker Compose lo monta automáticamente:

```yaml
# En compose.yaml (línea 12)
volumes:
  - ./infra/postgres/init.sql:/docker-entrypoint-initdb.d/00-init.sql:ro
```

Cuando corrés `docker compose up`, PostgreSQL ejecuta todos los `.sql` en `/docker-entrypoint-initdb.d/` en orden alfabético.

**Para verificar que funcionó:**
```bash
docker compose exec db psql -U postgres -d rag -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
```

---

## Para engineers / seniors

### Responsabilidades (SRP)

Esta carpeta DEBE contener:
- Scripts de inicialización de PostgreSQL (extensiones, configuración inicial)
- Archivos que se ejecutan UNA VEZ al crear el volumen

Esta carpeta NO DEBE contener:
- Migraciones de schema (eso lo maneja Alembic en `apps/backend/alembic/`)
- Datos de seed (eso va en scripts de la app)
- Backups
- Configuración de conexión (eso va en env vars)

### Colaboradores y dependencias

| Consumidor | Cómo lo usa |
|------------|-------------|
| `compose.yaml:12` | Monta como `/docker-entrypoint-initdb.d/00-init.sql` |
| PostgreSQL entrypoint | Ejecuta scripts en orden alfabético al init |
| `apps/backend/alembic/` | Asume que vector extension ya existe |

### Contratos / Interfaces

- **Input:** PostgreSQL container con volumen vacío (primera ejecución)
- **Output:** Base de datos con extensión `vector` habilitada
- **Idempotencia:** Sí (`IF NOT EXISTS` permite re-ejecución sin error)

### Flujo de trabajo típico

**"Necesito agregar otra extensión (ej: pg_trgm)":**
1. Editar `init.sql`, agregar `CREATE EXTENSION IF NOT EXISTS pg_trgm;`
2. Para aplicar: borrar volumen y recrear DB:
   ```bash
   docker compose down -v
   docker compose up -d db
   ```

**"El backend dice 'extension vector does not exist'":**
1. Verificar que el volumen se creó correctamente
2. Verificar mount en compose
3. Solución nuclear:
   ```bash
   docker compose down -v  # Borra volúmenes
   docker compose up -d    # Recrea desde cero
   ```

### Riesgos y pitfalls

| Riesgo | Causa | Solución |
|--------|-------|----------|
| Script no se ejecuta | Volumen ya existía | Borrar volumen: `docker volume rm rag-corp_pgdata` |
| Script falla silenciosamente | Syntax error en SQL | Ver logs: `docker compose logs db` |
| Orden incorrecto | Nombre de archivo | Prefijo `00-` asegura que corre primero |

### Seguridad / Compliance

- El script NO contiene credenciales
- La extensión `vector` no tiene implicaciones de seguridad adicionales

---

## CRC (Component/Folder CRC Card)

**Name:** `infra/postgres/`

**Responsibilities:**
1. Habilitar extensión pgvector en PostgreSQL
2. Mantener script idempotente (re-ejecutable sin errores)

**Collaborators:**
- Docker Compose (monta el archivo)
- PostgreSQL entrypoint (ejecuta el script)
- Alembic migrations (asumen extensión existe)

**Constraints:**
- Debe usar `IF NOT EXISTS` para idempotencia
- El schema real lo maneja Alembic, NO este script
- Solo se ejecuta con volumen vacío (primera vez)

---

## Evidencia

- `infra/postgres/init.sql:14` — `CREATE EXTENSION IF NOT EXISTS vector;`
- `compose.yaml:12` — mount del archivo
- `compose.yaml:4-7` — definición del servicio `db` con imagen `pgvector/pgvector`

---

## FAQ rápido

**¿Puedo borrar esto?**
No. Sin pgvector, el backend no puede guardar ni buscar embeddings.

**¿Por qué no está en Alembic?**
Porque la extensión debe existir ANTES de que Alembic cree tablas que la usan.

**¿Qué pasa si edito esto después de crear la DB?**
Nada automático. Tenés que borrar el volumen y recrear, o ejecutar el SQL manualmente.

---

## Glosario

| Término | Definición |
|---------|------------|
| **pgvector** | Extensión de PostgreSQL para almacenar y buscar vectores (arrays de números) |
| **Embedding** | Representación numérica de texto, generada por un modelo de IA |
| **Extension** | Plugin de PostgreSQL que agrega funcionalidad |
| **docker-entrypoint-initdb.d** | Carpeta especial donde PostgreSQL busca scripts de inicialización |
| **Idempotente** | Que puede ejecutarse múltiples veces sin cambiar el resultado |
