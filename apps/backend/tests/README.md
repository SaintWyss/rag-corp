# tests

El laboratorio del backend: corre suites por nivel y comparte un set único de fixtures/configuración.

## 🎯 Misión

Este directorio centraliza la **estrategia de pruebas del backend** (unit/integration/e2e) y la **configuración compartida** de Pytest para que todas las suites corran con el mismo contrato.

Recorridos rápidos por intención:

* **Quiero feedback rápido sin IO** → `unit/`
* **Quiero validar DB real + migraciones** → `integration/`
* **Quiero reservar espacio para flujos completos** → `e2e/`

### Qué SÍ hace

* Define fixtures compartidas en `conftest.py`.
* Organiza tests por nivel: `unit/`, `integration/`, `e2e/`.
* Se apoya en `../pytest.ini` para discovery, markers y coverage.

### Qué NO hace (y por qué)

* No contiene código de aplicación.

  * **Razón:** tests solo consumen `app/` como caja negra.
  * **Impacto:** cambios de negocio van en `app/`; acá solo se validan comportamientos.
* No sustituye la documentación de ejecución del backend.

  * **Razón:** el setup del stack y los comandos viven en el README del backend.
  * **Impacto:** si el entorno (DB/settings) está mal, acá solo vas a ver el fallo.

## 🗺️ Mapa del territorio

| Recurso        | Tipo           | Responsabilidad (en humano)                                                |
| :------------- | :------------- | :------------------------------------------------------------------------- |
| `__init__.py`  | Archivo Python | Marca el paquete de tests.                                                 |
| `conftest.py`  | Archivo Python | Fixtures y configuración global de Pytest (env de test, factories, mocks). |
| `unit/`        | Carpeta        | Tests unitarios (rápidos) por capa.                                        |
| `integration/` | Carpeta        | Tests de integración con DB real y migraciones.                            |
| `e2e/`         | Carpeta        | Tests end-to-end (espacio reservado).                                      |
| `README.md`    | Documento      | Esta documentación.                                                        |

## ⚙️ ¿Cómo funciona por dentro?

Input → Proceso → Output, siguiendo el flujo real de Pytest.

* **Input:** comando `pytest ...`.
* **Proceso:**

  1. Pytest descubre tests en `tests/` según patrones `test_*.py`.
  2. Carga `tests/conftest.py` y registra fixtures compartidas.
  3. Ejecuta tests por carpeta (unit/integration/e2e) y aplica markers.
  4. Genera coverage según `../pytest.ini`.
* **Output:** reporte en terminal + artefactos de coverage (si están habilitados).

Tecnologías/librerías usadas acá:

* `pytest`, `pytest-cov`, `pytest-asyncio`.

## 🔗 Conexiones y roles

* **Rol arquitectónico:** Tests.
* **Recibe órdenes de:** desarrolladores y CI.
* **Llama a:** código en `app/` y (en integración) recursos reales como DB.
* **Reglas de límites:** tests validan comportamiento; no modifican lógica de producción.

## 👩‍💻 Guía de uso (Snippets)

### 1) Correr todo desde `apps/backend/`

```bash
cd apps/backend
pytest
```

### 2) Unit tests

```bash
cd apps/backend
pytest -m unit tests/unit
```

### 3) Integration tests

```bash
cd apps/backend
pytest -m integration tests/integration
```

### 4) Ejecutar pytest desde Python

```python
import pytest

exit_code = pytest.main(["-v", "tests/unit"])
assert exit_code == 0
```

## 🧩 Cómo extender sin romper nada

* Agregá tests en la carpeta del nivel adecuado (`unit/`, `integration/`, `e2e/`).
* Reutilizá fixtures de `conftest.py` antes de crear nuevas.
* Etiquetá tests con markers existentes (`unit`, `integration`, `e2e`) y declaralos en `../pytest.ini` si agregás uno nuevo.
* En integración: mantené aislamiento (DB preparada, datos por test, cleanup cuando aplique).

## 🆘 Troubleshooting

* **`UndefinedTable`** → migraciones no aplicadas → correr Alembic (ver `../alembic/README.md`) y reintentar.
* **`ModuleNotFoundError: app`** → cwd incorrecto → ejecutar `pytest` desde `apps/backend/`.
* **Warnings de NumPy** → ruido del entorno → revisar `../pytest.ini` y el venv.
* **Tests de integración fallan conectando a DB** → DB caída/URL incorrecta → revisar variables de entorno y `docker compose`.

## 🔎 Ver también

* `./unit/README.md`
* `./integration/README.md`
* `./e2e/README.md`
* `../pytest.ini`
