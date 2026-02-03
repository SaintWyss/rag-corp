# repositories

Como un **archivo físico**: guarda y recupera registros con SQL o memoria, sin meter reglas de negocio.

## 🎯 Misión

Este módulo implementa repositorios concretos del dominio sobre **Postgres** (persistencia real) o **in‑memory** (tests/dev), manteniendo contratos estables para que la capa Application pueda orquestar casos de uso sin conocer SQL.

Acá vive todo lo que es **persistencia y mapeo**: SQL parametrizado, transformaciones fila → entidad/VO, transacciones y scoping por `workspace_id` cuando aplica.

Recorridos rápidos por intención:

- **Quiero ver el catálogo de repos Postgres** → `postgres/README.md`
- **Quiero ver repos in‑memory (tests/dev)** → `in_memory/README.md`
- **Quiero ver qué contratos debo implementar** → `../../domain/repositories.py`
- **Quiero ver cómo se obtiene la conexión/pool** → `../db/README.md`

### Qué SÍ hace

- Provee repositorios Postgres para documentos, workspaces, usuarios y auditoría (según puertos del dominio).
- Provee repositorios in‑memory para tests y desarrollo local.
- Encapsula SQL y mapeo fila → entidades/objetos de valor.
- Asegura límites operativos básicos: SQL parametrizado, scoping y transacciones donde corresponde.

### Qué NO hace (y por qué)

- No contiene reglas de negocio.
  - **Razón:** las decisiones viven en Domain/Application.
  - **Impacto:** si un repositorio “decide permisos” o “cambia estados por política”, se rompe trazabilidad y se duplica lógica.

- No expone endpoints HTTP ni conoce FastAPI.
  - **Razón:** el transporte pertenece a Interfaces.
  - **Impacto:** el repo se usa igual desde API o worker.

## 🗺️ Mapa del territorio

| Recurso       | Tipo           | Responsabilidad (en humano)                                            |
| :------------ | :------------- | :--------------------------------------------------------------------- |
| `__init__.py` | Archivo Python | Facade de exports (imports estables hacia implementaciones).           |
| `postgres/`   | Carpeta        | Implementaciones sobre Postgres: SQL, mappers, helpers de transacción. |
| `in_memory/`  | Carpeta        | Implementaciones en memoria para tests/dev (sin DB).                   |
| `README.md`   | Documento      | Portada + índice de repositorios (este documento).                     |

## ⚙️ ¿Cómo funciona por dentro?

Input → Proceso → Output.

### 1) Desde Application hacia un puerto

- **Input:** un use case llama un método del puerto (ej. `DocumentRepository.save(...)`).
- **Proceso:** el Container inyecta una implementación (Postgres o in‑memory) que cumple el Protocol.
- **Output:** entidad persistida/recuperada o valores simples.

### 2) Implementación Postgres

- **Input:** parámetros del método (ids, filtros, límites).
- **Proceso:**
  1. el repo obtiene una conexión desde `infrastructure/db` (`get_pool().connection()`).
  2. ejecuta **SQL parametrizado** (sin string interpolation peligrosa).
  3. mapea filas a entidades/VO del dominio.
  4. cuando aplica, envuelve con transacción (`with conn.transaction():`).

- **Output:** entidades/VO ya tipadas, listas para Application.

### 3) Implementación in‑memory

- **Input:** parámetros del método.
- **Proceso:** usa estructuras locales (dict/list) para simular persistencia y facilitar unit tests.
- **Output:** mismos tipos que Postgres (mismo contrato), sin depender de DB.

Conceptos mínimos en contexto:

- **Repo (Repository):** abstracción de persistencia orientada al dominio (no un “DAO genérico”).
- **Mapping:** traducir filas/JSON a entidades/VO.
- **Scoping:** cuando hay multi‑tenancy por workspace, el SQL filtra por `workspace_id`.

## 🔗 Conexiones y roles

- **Rol arquitectónico:** Infrastructure adapter (persistencia).

- **Recibe órdenes de:**
  - Application (use cases), que depende de Protocols de `app/domain/repositories.py`.

- **Llama a:**
  - `app/infrastructure/db/` para obtener conexiones (Postgres).
  - Estructuras locales (in‑memory).

- **Reglas de límites (imports/ownership):**
  - Debe respetar los Protocols del dominio sin cambiar firmas.
  - Puede depender de `infrastructure/db`, pero no de HTTP.
  - No importa casos de uso (Application) ni mete decisiones de policy.

## 👩‍💻 Guía de uso (Snippets)

### 1) Crear un repo Postgres (vía Container, recomendado)

```python
from app.container import get_document_repository

repo = get_document_repository()
```

### 2) Uso directo (tests/integración)

```python
from app.infrastructure.repositories.postgres import PostgresDocumentRepository

repo = PostgresDocumentRepository()
```

### 3) Patrón típico dentro de un método (Postgres)

```python
from app.infrastructure.db.pool import get_pool

class ExampleRepository:
    def ping(self) -> int:
        with get_pool().connection() as conn:
            row = conn.execute("SELECT 1").fetchone()
            return int(row[0])
```

### 4) In‑memory para unit tests

```python
from app.infrastructure.repositories.in_memory import InMemoryDocumentRepository

repo = InMemoryDocumentRepository()
```

## 🧩 Cómo extender sin romper nada

Checklist práctico:

1. **Cambiaste un puerto (Protocol)** → actualizá **todas** las implementaciones (Postgres + in‑memory) y los tests.
2. **SQL parametrizado siempre** → nada de interpolar strings con inputs.
3. **Scoping por `workspace_id`** cuando aplique → evitar leaks multi‑tenant.
4. **Transacciones explícitas** para operaciones compuestas (write + write).
5. **Mapping estable** → si cambia una entidad, actualizar mapper y tests.
6. **Integración**:
   - tests de integración con Postgres real para queries críticas.
   - tests de unidad para lógica de mapping (sin DB) cuando sea posible.

## 🆘 Troubleshooting

- **`relation "..." does not exist`** → migraciones pendientes → revisar `apps/backend/alembic/` y correr migrations.
- **Resultados vacíos inesperados** → `workspace_id` incorrecto o faltante en el filtro → revisar el use case y el SQL del repo.
- **Errores de pool / no inicializado** → falta `init_pool()` en startup → revisar `../db/pool.py` y el bootstrap del API/worker.
- **Violaciones de unique/foreign key** → datos inconsistentes o falta de validación previa → revisar constraints y el orden de writes.
- **Query lenta** → índice faltante o filtro no selectivo → revisar SQL en `postgres/` y usar EXPLAIN en entorno de DB.

## 🔎 Ver también

- `./postgres/README.md` (repositorios Postgres)
- `./in_memory/README.md` (repositorios en memoria)
- `../../domain/repositories.py` (Protocols de persistencia)
- `../db/README.md` (pool e instrumentación de DB)
