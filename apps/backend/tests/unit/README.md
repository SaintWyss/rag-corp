# unit
Como un **microscopio**: valida piezas individuales sin IO real.

## 🎯 Misión
Este directorio contiene tests unitarios: validan funciones, clases y casos de uso en aislamiento usando mocks/fakes.

### Qué SÍ hace
- Prueba lógica aislada sin DB/Redis/S3.
- Usa dobles desde `tests/conftest.py`.
- Provee feedback rápido y determinista.

### Qué NO hace (y por qué)
- No toca servicios externos reales.
  - Razón: el objetivo es aislar lógica.
  - Consecuencia: la integración con DB/Redis se valida en `tests/integration/`.
- No cubre flujos end-to-end.
  - Razón: el alcance de unit es “pieza”, no “sistema”.
  - Consecuencia: los flujos completos viven en `tests/e2e/`.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :-- | :-- | :-- |
| `README.md` | Documento | Guía de tests unitarios. |
| `__init__.py` | Archivo Python | Marca el paquete. |
| `api/` | Carpeta | Unit tests de adaptadores HTTP/schemas. |
| `application/` | Carpeta | Unit tests de casos de uso. |
| `domain/` | Carpeta | Unit tests de reglas y entidades. |
| `identity/` | Carpeta | Unit tests de auth/roles/permisos. |
| `infrastructure/` | Carpeta | Unit tests de adapters con fakes. |
| `worker/` | Carpeta | Unit tests de jobs y builders. |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output.

- **Input:** `pytest tests/unit -m unit`.
- **Proceso:** carga `tests/conftest.py`, reemplaza puertos por fakes/mocks y ejecuta pruebas por carpeta.
- **Output:** reporte rápido y determinista.

## 🔗 Conexiones y roles
- **Rol arquitectónico:** tests unitarios.
- **Recibe órdenes de:** desarrolladores y CI.
- **Llama a:** módulos de `app/` con dependencias reemplazadas.
- **Reglas de límites:** no IO real, no red, no tiempo real sin control.

## 👩‍💻 Guía de uso (Snippets)
```bash
cd apps/backend
pytest -m unit tests/unit
```

```bash
# Ejecutar solo application
pytest -m unit tests/unit/application -q
```

```python
# Ejecutar desde Python
import pytest
pytest.main(["-v", "tests/unit", "-m", "unit"])
```

## 🧩 Cómo extender sin romper nada
- Ubicá el test en la carpeta de la capa correspondiente.
- Usá fakes/mocks para puertos del dominio.
- Evitá sleeps y dependencias de tiempo real.
- Si necesitás wiring, usá `app/container.py` pero overrideá con fakes en el test.
- Tests: este módulo en `apps/backend/tests/unit/`.

## 🆘 Troubleshooting
- **Síntoma:** tests lentos.
  - **Causa probable:** IO real accidental.
  - **Dónde mirar:** fixtures y dobles en `tests/conftest.py`.
  - **Solución:** reemplazar dependencias por fakes/mocks.
- **Síntoma:** fixtures no encontradas.
  - **Causa probable:** nombre o scope incorrecto.
  - **Dónde mirar:** `tests/conftest.py`.
  - **Solución:** corregir nombre/scope.
- **Síntoma:** `ModuleNotFoundError: app`.
  - **Causa probable:** cwd incorrecto.
  - **Dónde mirar:** `pwd`.
  - **Solución:** ejecutar desde `apps/backend/`.
- **Síntoma:** tests flaky.
  - **Causa probable:** dependencia de orden o tiempo.
  - **Dónde mirar:** tests afectados.
  - **Solución:** fijar seeds y eliminar estado global.

## 🔎 Ver también
- `../README.md`
- `../integration/README.md`
- `../e2e/README.md`
- `../../conftest.py`
