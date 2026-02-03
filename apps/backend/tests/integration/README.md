# integration

Como un **ensayo general**: valida el backend con piezas reales (Postgres + composición de API) sin ir al “full stack” externo.

## 🎯 Misión

Este directorio contiene **tests de integración**: verifican que el backend funcione con dependencias reales (principalmente **Postgres**) y que flujos críticos se ejecuten de punta a punta **a nivel de componentes** (API + repos + seguridad RAG).

Recorridos rápidos por intención:

- **Quiero validar endpoints HTTP sin levantar un servidor** → `test_api_endpoints.py`
- **Quiero validar repositorios Postgres reales** → `test_postgres_document_repo.py`
- **Quiero validar controles de seguridad en búsquedas RAG** → `test_rag_security_pack.py`

### Qué SÍ hace

- Prueba endpoints HTTP usando `FastAPI TestClient` sobre la app compuesta.
- Verifica repositorios reales contra Postgres (incluye constraints, índices y consultas reales).
- Valida el paquete de seguridad RAG (filtros/guardrails aplicados a queries y/o chunks).
- Asegura que las migraciones estén aplicadas antes de ejecutar casos que dependen del esquema.

### Qué NO hace (y por qué)

- No sustituye los tests unitarios.
  - **Razón:** el unit test es el guardián principal de lógica en aislamiento.
  - **Impacto:** si un caso falla en integración, suele haber un unit que también debería existir.

- No cubre escenarios full e2e con infraestructura externa completa.
  - **Razón:** acá el foco es Postgres + composición; servicios externos pueden estar fakeados.
  - **Impacto:** flujos con worker/cola/storage reales (si aplican) viven en `tests/e2e/`.

## 🗺️ Mapa del territorio

| Recurso                          | Tipo           | Responsabilidad (en humano)                                                                          |
| :------------------------------- | :------------- | :--------------------------------------------------------------------------------------------------- |
| `__init__.py`                    | Archivo Python | Marca el paquete de integración.                                                                     |
| `conftest.py`                    | Archivo Python | Fixtures de integración: DB real, pool/conexión, app compuesta para TestClient, helpers de limpieza. |
| `test_api_endpoints.py`          | Test           | Verifica endpoints HTTP clave (status codes, contratos, validaciones, auth básica).                  |
| `test_postgres_document_repo.py` | Test           | Prueba repositorios Postgres reales (persistencia/lectura, queries e invariantes).                   |
| `test_rag_security_pack.py`      | Test           | Valida reglas de seguridad RAG (filtros anti-inyección, políticas por rol, sanitización).            |
| `README.md`                      | Documento      | Esta documentación.                                                                                  |

## ⚙️ ¿Cómo funciona por dentro?

Input → Proceso → Output.

- **Input:** `pytest tests/integration -m integration`.
- **Proceso:**
  1. Pytest descubre tests bajo `tests/integration/`.
  2. Carga `tests/conftest.py` (global) y luego `tests/integration/conftest.py` (específico).
  3. Se prepara una DB real (según `DATABASE_URL`) y se asegura el esquema:
     - si el entorno está pensado para integración, aplica migraciones (Alembic `upgrade head`).
     - si la DB no está lista, falla con error explícito (`UndefinedTable`, conexión, etc.).

  4. Se construye la app FastAPI para `TestClient` usando la composición real (container/settings) y dobles donde aplique.
  5. Cada test ejecuta requests HTTP o llamadas a repositorios reales y valida:
     - status codes + payloads.
     - invariantes del modelo en DB.
     - reglas de seguridad en el pipeline RAG.

- **Output:** reporte de integración (más lento que unit) y evidencia de que “la pieza Postgres” funciona.

Tecnologías/librerías usadas acá:

- `pytest`, `fastapi.testclient`, `psycopg`.

## 🔗 Conexiones y roles

- **Rol arquitectónico:** Tests (integration).

- **Recibe órdenes de:** desarrolladores/CI.

- **Llama a:**
  - Postgres real (y extensiones requeridas por el esquema).
  - composición de API (FastAPI app) vía imports del backend.
  - servicios que el container configure (algunos pueden ser fakes según settings).

- **Reglas de límites:**
  - requiere DB accesible y con migraciones aplicadas.
  - no debe depender de red externa (LLM/embeddings reales) salvo que el repo lo habilite explícitamente con un flag.

## 👩‍💻 Guía de uso (Snippets)

### 1) Correr integración desde `apps/backend/`

```bash
cd apps/backend
pytest -m integration tests/integration
```

### 2) Apuntar a una DB de integración (ejemplo)

```bash
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/rag"
cd apps/backend
pytest -m integration tests/integration -v
```

### 3) Correr un test puntual

```bash
cd apps/backend
pytest -m integration -v tests/integration/test_postgres_document_repo.py
```

### 4) Ejecutar pytest desde Python

```python
import pytest

exit_code = pytest.main(["-v", "tests/integration", "-m", "integration"])
assert exit_code == 0
```

## 🧩 Cómo extender sin romper nada

Checklist práctico:

1. Elegí la forma de integración:
   - endpoint HTTP → agregar caso en `test_api_endpoints.py` (o crear `test_api_<feature>.py`).
   - repos Postgres → agregar casos en `test_postgres_*_repo.py`.
   - seguridad RAG → agregar casos en `test_rag_security_pack.py`.

2. Mantené los tests idempotentes:
   - datos de prueba propios por test.
   - limpiar tablas/fixtures cuando aplique.

3. Si agregás tablas/campos:
   - asegurá migración Alembic.
   - actualizá factories/fixtures de integración.

4. Si necesitás un fake para un servicio externo:
   - habilitalo por settings/feature flag (no hardcode en el test).
   - documentalo en este README.

## 🆘 Troubleshooting

- **`UndefinedTable`** → migraciones faltantes → correr Alembic (`../../alembic/README.md`) o levantar el servicio de migración y reintentar.
- **Conexión rechazada / timeout** → DB apagada o URL incorrecta → revisar `DATABASE_URL` y `docker compose ps`.
- **Errores de pgvector / extensión faltante** → Postgres sin extensiones requeridas → usar la DB del compose o instalar extensiones en el servidor.
- **Endpoints 401/403** → auth activa o credenciales inválidas → revisar settings de test (tokens/API keys) y fixtures de auth.
- **Fallas intermitentes (flaky)** → datos compartidos entre tests → aislar por test (transacciones/cleanup) y evitar orden-dependencia.

## 🔎 Ver también

- `../README.md` (índice de tests)
- `../unit/README.md` (aislamiento y dobles)
- `../e2e/README.md` (flujos completos)
- `../../alembic/README.md` (migraciones)
- `../../../scripts/README.md` (bootstrap y tooling)
