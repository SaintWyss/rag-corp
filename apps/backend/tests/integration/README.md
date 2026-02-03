# integration
Como un **ensayo general**: valida integración real con DB y composición de API.

## 🎯 Misión
Este directorio contiene tests de integración que verifican el backend con dependencias reales (principalmente Postgres) y composición real de la API.

### Qué SÍ hace
- Usa FastAPI `TestClient` para endpoints sin levantar servidor.
- Verifica repositorios Postgres reales.
- Ejecuta pruebas marcadas como `integration`.

### Qué NO hace (y por qué)
- No reemplaza unit tests. Razón: el unit test es el primer guardián de lógica aislada. Consecuencia: si falta un unit test, integración no lo compensa.
- No cubre infraestructura completa (worker/colas) salvo que se agregue explícitamente. Razón: el alcance es Postgres + composición. Consecuencia: flujos full-stack quedan para `tests/e2e/`.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :-- | :-- | :-- |
| `README.md` | Documento | Guía de integración. |
| `__init__.py` | Archivo Python | Marca el paquete. |
| `conftest.py` | Archivo Python | Fixtures de integración (DB/app). |
| `test_api_endpoints.py` | Test | Endpoints HTTP con TestClient. |
| `test_postgres_document_repo.py` | Test | Repositorios Postgres reales. |
| `test_rag_security_pack.py` | Test | Reglas de seguridad RAG. |
## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output.

- **Input:** `pytest -m integration tests/integration`.
- **Proceso:** carga `tests/conftest.py` y fixtures locales, prepara DB real y ejecuta tests.
- **Output:** reporte de integración.

## 🔗 Conexiones y roles
- **Rol arquitectónico:** tests de integración.
- **Recibe órdenes de:** desarrolladores/CI.
- **Llama a:** Postgres real y composición FastAPI.
- **Reglas de límites:** no depender de red externa salvo flags explícitos.

## 👩‍💻 Guía de uso (Snippets)
```bash
# Ejecutar integración
cd apps/backend
pytest -m integration tests/integration
```

```bash
# Habilitar integración en tests que lo requieren
export RUN_INTEGRATION=1
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/rag"
pytest -m integration tests/integration -v
```

```bash
# Tests de API (requieren GOOGLE_API_KEY)
export GOOGLE_API_KEY=... 
pytest -m integration tests/integration/test_api_endpoints.py
```

## 🧩 Cómo extender sin romper nada
- Agregá tests nuevos en este directorio y marcá con `@pytest.mark.integration`.
- Reutilizá fixtures de `tests/conftest.py` y `tests/integration/conftest.py`.
- Si agregás tablas/campos, agregá migración en `apps/backend/alembic/`.
- Wiring: si necesitás servicios reales, obtenelos desde `app/container.py`.
- Tests: este módulo en `apps/backend/tests/integration/`.

## 🆘 Troubleshooting
- **Síntoma:** tests se skipean.
- **Causa probable:** falta `RUN_INTEGRATION=1` o `GOOGLE_API_KEY`.
- **Dónde mirar:** encabezados de `test_api_endpoints.py`.
- **Solución:** setear variables y reintentar.
- **Síntoma:** `UndefinedTable`.
- **Causa probable:** migraciones no aplicadas.
- **Dónde mirar:** `apps/backend/alembic/README.md`.
- **Solución:** `alembic upgrade head`.
- **Síntoma:** conexión rechazada.
- **Causa probable:** DB apagada o URL incorrecta.
- **Dónde mirar:** `DATABASE_URL` y `docker compose`.
- **Solución:** levantar DB y corregir URL.
- **Síntoma:** 401/403 en endpoints.
- **Causa probable:** auth activa sin credenciales.
- **Dónde mirar:** fixtures de auth y settings.
- **Solución:** usar headers/tokens válidos en el test.

## 🔎 Ver también
- `../README.md`
- `../unit/README.md`
- `../e2e/README.md`
- `../../alembic/README.md`
