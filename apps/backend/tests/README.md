# Tests (root)

## 🎯 Misión
Centralizar la estrategia de pruebas del backend: unitarias, integración y e2e con una configuración común (`conftest.py`).

**Qué SÍ hace**
- Define fixtures compartidas.
- Organiza tests por nivel (unit/integration/e2e).
- Configura Pytest para el backend.

**Qué NO hace**
- No contiene código de aplicación.
- No sustituye la documentación de ejecución del backend.

**Analogía (opcional)**
- Es el “laboratorio” donde se valida que todo funcione.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :--- | :--- | :--- |
| 🐍 `__init__.py` | Archivo Python | Marca el paquete de tests. |
| 🐍 `conftest.py` | Archivo Python | Fixtures y configuración compartida de Pytest. |
| 📁 `e2e/` | Carpeta | Tests end‑to‑end (pocos o por definir). |
| 📁 `integration/` | Carpeta | Tests de integración con DB real. |
| 📄 `README.md` | Documento | Esta documentación. |
| 📁 `unit/` | Carpeta | Tests unitarios por capa. |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output:
- **Input**: comando `pytest`.
- **Proceso**: Pytest carga fixtures de `conftest.py` y ejecuta tests por carpeta.
- **Output**: reporte de resultados y coverage según `pytest.ini`.

Tecnologías/librerías usadas aquí:
- pytest, pytest-cov, pytest-asyncio.

Flujo típico:
- `pytest` descubre tests en `tests/`.
- Fixtures configuran env y mocks.
- Coverage se genera según `pytest.ini`.

## 🔗 Conexiones y roles
- Rol arquitectónico: Tests.
- Recibe órdenes de: desarrolladores/CI.
- Llama a: código en `app/` y recursos reales en integración.
- Contratos y límites: tests no deben modificar la lógica de producción.

## 👩‍💻 Guía de uso (Snippets)
Comandos típicos:
- `pytest`
- `pytest tests/unit -m unit`
- `pytest tests/integration -m integration`

```python
import pytest

exit_code = pytest.main(["-v", "tests/unit"])
assert exit_code == 0
```

## 🧩 Cómo extender sin romper nada
- Agrega tests en la carpeta del nivel adecuado.
- Reutiliza fixtures de `conftest.py`.
- Etiqueta tests con markers (`unit`, `integration`).
- Mantén tests de integración aislados y con DB disponible.

## 🆘 Troubleshooting
- Síntoma: `UndefinedTable` → Causa probable: migraciones no aplicadas → Ejecutar Alembic.
- Síntoma: `ModuleNotFoundError: app` → Causa probable: cwd incorrecto → Ejecutar desde `apps/backend/`.
- Síntoma: warnings de numpy → Causa probable: reload de numpy → Ver `pytest.ini`.

## 🔎 Ver también
- [Unit tests](./unit/README.md)
- [Integration tests](./integration/README.md)
- [E2E tests](./e2e/README.md)
