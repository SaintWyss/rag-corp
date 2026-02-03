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

- No contiene reglas de negocio. Razón: ** las decisiones viven en Domain/Application. Impacto: ** si un repositorio “decide permisos” o “cambia estados por política”, se rompe trazabilidad y se duplica lógica.

- No expone endpoints HTTP ni conoce FastAPI. Razón: ** el transporte pertenece a Interfaces. Impacto: ** el repo se usa igual desde API o worker.

## 🗺️ Mapa del territorio

| Recurso | Tipo | Responsabilidad (en humano) |
| :------------ | :------------- | :--------------------------------------------------------------------- |
| `__init__.py` | Archivo Python | Facade de exports (imports estables hacia implementaciones). |
| `postgres` | Carpeta | Implementaciones sobre Postgres: SQL, mappers, helpers de transacción. |
| `in_memory` | Carpeta | Implementaciones en memoria para tests/dev (sin DB). |
| `README.md` | Documento | Portada + índice de repositorios (este documento). |

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
```python
# Por qué: muestra el contrato mínimo del módulo.
from app.container import get_document_repository
repo = get_document_repository()
```

```python
# Por qué: ejemplo de integración sin infraestructura real.
from app.infrastructure.repositories.postgres import PostgresDocumentRepository
repo = PostgresDocumentRepository()
```

```python
# Por qué: deja visible el flujo principal.
from app.infrastructure.repositories.in_memory import InMemoryWorkspaceRepository
repo = InMemoryWorkspaceRepository()
```

## 🧩 Cómo extender sin romper nada
- Si agregás un método en un puerto, actualizá Postgres e in-memory.
- Mantener SQL parametrizado y scoping por `workspace_id`.
- Cablear repositorios en `app/container.py`.
- Tests: integration para queries críticas en `apps/backend/tests/integration/`.

## 🆘 Troubleshooting
- **Síntoma:** `relation does not exist`.
- **Causa probable:** migraciones pendientes.
- **Dónde mirar:** `apps/backend/alembic/`.
- **Solución:** `alembic upgrade head`.
- **Síntoma:** resultados vacíos.
- **Causa probable:** `workspace_id` incorrecto.
- **Dónde mirar:** SQL en repositorio.
- **Solución:** revisar scoping y filtros.
- **Síntoma:** `PoolNotInitializedError`.
- **Causa probable:** pool no inicializado.
- **Dónde mirar:** `db/pool.py`.
- **Solución:** inicializar pool en startup.
- **Síntoma:** divergencia entre in-memory y Postgres.
- **Causa probable:** métodos no alineados.
- **Dónde mirar:** `in_memory/` vs `postgres/`.
- **Solución:** mantener paridad en contratos.

## 🔎 Ver también
- `./postgres/README.md`
- `./in_memory/README.md`
- `../../domain/repositories.py`
- `../db/README.md`
