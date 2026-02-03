# unit

Como un **microscopio**: valida piezas individuales del backend con dobles, sin tocar IO real.

## 🎯 Misión

Este directorio contiene **tests unitarios**: validan comportamientos de funciones, clases y casos de uso en aislamiento, con dependencias reemplazadas por **mocks/fakes** definidos en fixtures.

Recorridos rápidos por intención:

- **Quiero testear un router/DTO sin levantar FastAPI** → `api/`
- **Quiero validar un use case sin DB/Redis/S3** → `application/`
- **Quiero validar reglas puras de negocio** → `domain/`
- **Quiero validar permisos/roles/autenticación** → `identity/`
- **Quiero validar adaptadores con dobles (sin IO)** → `infrastructure/`
- **Quiero validar jobs sin cola real** → `worker/`

### Qué SÍ hace

- Prueba módulos en aislamiento (una unidad por test, foco en comportamiento).
- Usa dobles controlados (mocks/fakes/stubs) desde `tests/conftest.py`.
- Corre rápido y determinista (ideal para feedback continuo y CI).
- Aporta cobertura útil: ramas de error, validaciones y límites (fail-fast).

### Qué NO hace (y por qué)

- No requiere DB real ni servicios externos.
  - **Razón:** el objetivo es aislar lógica; el IO se valida en `tests/integration/`.
  - **Impacto:** si el comportamiento depende de SQL/Redis/S3 reales, este no es el nivel correcto.

- No prueba flujos end-to-end.
  - **Razón:** el E2E tiene otro alcance y otra latencia.
  - **Impacto:** acá se prueban piezas; el “camino completo” vive en `tests/e2e/` (cuando aplique).

## 🗺️ Mapa del territorio

| Recurso           | Tipo           | Responsabilidad (en humano)                                         |
| :---------------- | :------------- | :------------------------------------------------------------------ |
| `__init__.py`     | Archivo Python | Marca el paquete de tests unitarios.                                |
| `api/`            | Carpeta        | Tests unitarios de la capa de interfaces (mappers/DTOs/handlers).   |
| `application/`    | Carpeta        | Tests unitarios de casos de uso y orquestación (puertos mockeados). |
| `domain/`         | Carpeta        | Tests unitarios de reglas puras del dominio (sin infraestructura).  |
| `identity/`       | Carpeta        | Tests unitarios de auth, roles, claims y decisiones de permisos.    |
| `infrastructure/` | Carpeta        | Tests unitarios de adaptadores usando fakes (sin IO real).          |
| `worker/`         | Carpeta        | Tests unitarios de jobs/builders del worker (sin cola real).        |
| `README.md`       | Documento      | Esta documentación.                                                 |

## ⚙️ ¿Cómo funciona por dentro?

Input → Proceso → Output.

- **Input:** `pytest tests/unit -m unit`.
- **Proceso:**
  1. Pytest descubre tests bajo `tests/unit/`.
  2. Carga fixtures globales de `tests/conftest.py`.
  3. Cada test instancia la unidad bajo prueba con dobles:
     - repositorios como `Mock` o fakes en memoria.
     - servicios externos (LLM/embeddings/storage/queue) como stubs.

  4. Se validan salidas y efectos **observables** (resultado, llamadas, errores tipados).

- **Output:** reporte rápido y determinista + coverage (si está habilitado).

Tecnologías/librerías usadas acá:

- `pytest`, `unittest.mock`.

## 🔗 Conexiones y roles

- **Rol arquitectónico:** Tests (unit).
- **Recibe órdenes de:** desarrolladores/CI.
- **Llama a:** módulos de `app/` con dependencias reemplazadas.
- **Reglas de límites:**
  - no tocar DB/Redis/S3 reales.
  - no hacer llamadas de red.
  - no depender de reloj/aleatoriedad sin control (usar seeds o fakes).

## 👩‍💻 Guía de uso (Snippets)

### 1) Correr toda la suite unit

```bash
cd apps/backend
pytest -m unit tests/unit
```

### 2) Correr una carpeta (ej: application)

```bash
cd apps/backend
pytest -m unit tests/unit/application -q
```

### 3) Correr un test puntual

```bash
cd apps/backend
pytest -m unit -v tests/unit/application/test_upload_document_use_case.py
```

### 4) Ejecutar pytest desde Python (útil en debugging)

```python
import pytest

exit_code = pytest.main(["-v", "tests/unit", "-m", "unit"])
assert exit_code == 0
```

## 🧩 Cómo extender sin romper nada

Checklist práctico:

1. Elegí la ubicación por capa (`api/`, `application/`, `domain/`, `identity/`, `infrastructure/`, `worker/`).
2. Escribí tests **pequeños y específicos** (un comportamiento por caso).
3. Mockeá puertos del dominio con `Mock(spec=...)` o fakes explícitos.
4. Reutilizá fixtures de `tests/conftest.py` antes de crear nuevas.
5. Validá contratos, no implementación:
   - `result.error.code` y `result.status`, no “strings mágicos”.
   - llamadas clave (ej: `enqueue(...)`) con argumentos mínimos.

6. Mantené velocidad:
   - nada de sleeps.
   - nada de IO real.

## 🆘 Troubleshooting

- **Tests lentos** → hay IO real accidental (DB/red/FS) → revisar `conftest.py` y reemplazar dependencias por fakes/mocks.
- **Fixtures no encontradas** → import path o nombre de fixture incorrecto → revisar `tests/conftest.py` y el scope de fixtures.
- **`ModuleNotFoundError: app`** → estás fuera de `apps/backend/` → correr `pytest` desde ese directorio.
- **Flaky tests** → dependencia de tiempo/orden → fijar seeds, evitar estado global y usar fixtures `autouse` solo cuando haga falta.

## 🔎 Ver también

- `../README.md` (índice de tests)
- `../integration/README.md` (DB real y migraciones)
- `../e2e/README.md` (flujos completos)
- `../../conftest.py` (fixtures compartidas)
