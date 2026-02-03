# tests
Como un **laboratorio**: concentra fixtures y separa pruebas por nivel.

## 🎯 Misión
Este directorio define la **estrategia de pruebas** del backend y centraliza configuración compartida de Pytest para que todas las suites usen el mismo contrato.

### Qué SÍ hace
- Organiza suites por nivel: `unit/`, `integration/`, `e2e/`.
- Define fixtures compartidas en `conftest.py`.
- Usa `pytest.ini` para markers y coverage.

### Qué NO hace (y por qué)
- No contiene código de aplicación.
  - Razón: los tests consumen `app/` como caja negra.
  - Consecuencia: cambios de negocio van en `app/`, no en `tests/`.
- No define el entorno de infraestructura.
  - Razón: DB/Redis se definen fuera (compose/CI).
  - Consecuencia: si el entorno falla, los tests fallarán aunque estén correctos.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :-- | :-- | :-- |
| `README.md` | Documento | Índice de la estrategia de tests. |
| `__init__.py` | Archivo Python | Marca el paquete de tests. |
| `conftest.py` | Archivo Python | Fixtures y configuración global de Pytest. |
| `unit/` | Carpeta | Tests unitarios (sin IO real). |
| `integration/` | Carpeta | Tests de integración (DB real, composición real). |
| `e2e/` | Carpeta | Tests end-to-end (reservado). |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output.

- **Input:** `pytest` con markers.
- **Proceso:** Pytest descubre tests en `tests/`, carga `conftest.py` y aplica markers definidos en `pytest.ini`.
- **Output:** reporte en consola + coverage (si está habilitado).

## 🔗 Conexiones y roles
- **Rol arquitectónico:** tests.
- **Recibe órdenes de:** desarrolladores y CI.
- **Llama a:** `app/` y dependencias externas en integración.
- **Reglas de límites:** tests validan comportamiento, no reemplazan lógica de producción.

## 👩‍💻 Guía de uso (Snippets)
```bash
# Todo
cd apps/backend
pytest
```

```bash
# Unit
pytest -m unit tests/unit
```

```bash
# Integration
pytest -m integration tests/integration
```

```python
# Ejecutar desde Python
import pytest
pytest.main(["-v", "tests/unit", "-m", "unit"])
```

## 🧩 Cómo extender sin romper nada
- Elegí el nivel correcto (`unit/`, `integration/`, `e2e/`).
- Reutilizá fixtures en `tests/conftest.py`.
- Si agregás un marker, declaralo en `pytest.ini`.
- Si necesitás dependencias del runtime, obtenelas desde `app/container.py`.
- Tests: unit en `tests/unit/`, integration en `tests/integration/`, e2e en `tests/e2e/`.

## 🆘 Troubleshooting
- **Síntoma:** `UndefinedTable` en integración.
  - **Causa probable:** migraciones no aplicadas.
  - **Dónde mirar:** `apps/backend/alembic/README.md`.
  - **Solución:** `alembic upgrade head`.
- **Síntoma:** `ModuleNotFoundError: app`.
  - **Causa probable:** cwd incorrecto.
  - **Dónde mirar:** `pwd`.
  - **Solución:** correr desde `apps/backend/`.
- **Síntoma:** warnings ruidosos (NumPy/Deprecation).
  - **Causa probable:** config de warnings.
  - **Dónde mirar:** `pytest.ini`.
  - **Solución:** ajustar filtros o venv.
- **Síntoma:** integración falla conectando a DB.
  - **Causa probable:** `DATABASE_URL` inválida o DB apagada.
  - **Dónde mirar:** `.env`/compose.
  - **Solución:** levantar DB y corregir URL.

## 🔎 Ver también
- `./unit/README.md`
- `./integration/README.md`
- `./e2e/README.md`
- `../pytest.ini`
