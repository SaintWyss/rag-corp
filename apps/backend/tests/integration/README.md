# Tests de Integración

## 🎯 Misión
Verificar que el backend funcione con dependencias reales (principalmente Postgres) y que los flujos críticos se ejecuten end‑to‑end a nivel de componentes.

**Qué SÍ hace**
- Prueba endpoints HTTP con FastAPI TestClient.
- Verifica repositorios Postgres reales.
- Valida controles de seguridad en búsquedas RAG.

**Qué NO hace**
- No sustituye los tests unitarios.
- No cubre escenarios full e2e con infraestructura externa completa.

**Analogía (opcional)**
- Es el “ensayo general” con piezas reales.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :--- | :--- | :--- |
| 🐍 `__init__.py` | Archivo Python | Marca el paquete de integración. |
| 🐍 `conftest.py` | Archivo Python | Fixtures específicas de integración. |
| 📄 `README.md` | Documento | Esta documentación. |
| 🧪 `test_api_endpoints.py` | Test | Verifica endpoints HTTP. |
| 🧪 `test_postgres_document_repo.py` | Test | Prueba repositorios Postgres reales. |
| 🧪 `test_rag_security_pack.py` | Test | Valida filtros de seguridad en RAG. |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output:
- **Input**: `pytest tests/integration`.
- **Proceso**: tests llaman API/repos reales con DB conectada.
- **Output**: validación de flujos con infraestructura real.

Tecnologías/librerías usadas aquí:
- pytest, FastAPI TestClient, psycopg.

## 🔗 Conexiones y roles
- Rol arquitectónico: Tests (integration).
- Recibe órdenes de: desarrolladores/CI.
- Llama a: Postgres real y servicios configurados (fakes opcionales).
- Contratos y límites: requiere DB con migraciones aplicadas.

## 👩‍💻 Guía de uso (Snippets)
Comandos típicos:
- `pytest tests/integration -m integration`

```python
import pytest

pytest.main(["-v", "tests/integration", "-m", "integration"])
```

## 🧩 Cómo extender sin romper nada
- Asegura DB limpia y migrada antes de correr.
- Mantén los tests idempotentes.
- Si agregás una tabla, actualiza fixtures y datos de prueba.

## 🆘 Troubleshooting
- Síntoma: `UndefinedTable` → Causa probable: migraciones faltantes → Ejecutar Alembic.
- Síntoma: conexión rechazada → Causa probable: DB apagada → Revisar `DATABASE_URL`.
- Síntoma: endpoints 401/403 → Causa probable: auth habilitada → Revisar `.env` y API keys.

## 🔎 Ver también
- [Tests root](../README.md)
- [Alembic](../../alembic/README.md)
