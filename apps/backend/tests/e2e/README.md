# e2e

Como una **pista de pruebas**: lista para correr flujos completos cuando exista una suite end-to-end.

## 🎯 Misión

Este directorio reserva el espacio y las convenciones para **pruebas end-to-end** del backend contra un **entorno real** (DB/colas/storage/LLM según configuración), cuando esas suites estén disponibles.

Recorridos rápidos por intención:

- **Quiero correr flujos completos (cuando existan)** → `pytest -m e2e tests/e2e`
- **Quiero validar Postgres + API sin full stack** → ver `../integration/`
- **Quiero feedback rápido sin IO** → ver `../unit/`

### Qué SÍ hace

- Define el lugar y la convención para tests e2e (`tests/e2e/`).
- Deja preparado el wiring para correr suites completas desde CI o local cuando se agreguen.

### Qué NO hace (y por qué)

- No contiene tests e2e en este momento.
  - **Razón:** todavía no hay casos end-to-end definidos/estables.
  - **Impacto:** hoy la cobertura “de punta a punta” se logra con `tests/integration/`.

- No reemplaza integración ni unit tests.
  - **Razón:** unit e integración son el gate principal del repo.
  - **Impacto:** un e2e nuevo debe venir acompañado de unit/integration que cubran los fallos más probables.

## 🗺️ Mapa del territorio

| Recurso       | Tipo           | Responsabilidad (en humano) |
| :------------ | :------------- | :-------------------------- |
| `__init__.py` | Archivo Python | Marca el paquete e2e.       |
| `README.md`   | Documento      | Esta documentación.         |

## ⚙️ ¿Cómo funciona por dentro?

Input → Proceso → Output.

- **Input:** `pytest tests/e2e`.
- **Proceso:**
  1. Pytest descubre tests bajo `tests/e2e/`.
  2. Carga fixtures globales (`tests/conftest.py`) y (cuando existan) fixtures e2e específicas.
  3. Los tests ejecutan flujos completos contra un entorno real:
     - HTTP (API levantada o TestClient, según el diseño del e2e).
     - DB real.
     - cola/worker (si el flujo lo requiere).
     - storage real.
     - LLM/embeddings reales o fakes controlados por settings.

- **Output:** validación end-to-end (más lenta, mayor cobertura funcional).

Tecnologías/librerías usadas acá:

- `pytest`.

## 🔗 Conexiones y roles

- **Rol arquitectónico:** Tests (e2e).
- **Recibe órdenes de:** desarrolladores/CI.
- **Llama a:** entorno real con DB/colas/storage/LLM configurados.
- **Reglas de límites:**
  - requiere infraestructura completa disponible.
  - evita depender de red externa no controlada (si se usan vendors, proteger con flags y límites).

## 👩‍💻 Guía de uso (Snippets)

### 1) Correr e2e (placeholder)

```bash
cd apps/backend
pytest tests/e2e
```

### 2) Ejecutar pytest desde Python

```python
import pytest

exit_code = pytest.main(["-v", "tests/e2e"])
assert exit_code == 0
```

## 🧩 Cómo extender sin romper nada

Checklist práctico:

1. Definí el “entorno real” que querés validar (compose profile, servicios obligatorios).
2. Creá fixtures e2e que hagan setup/teardown:
   - base de datos limpia (migrada).
   - colas/workers listos.
   - storage con un bucket/path de test.

3. Evitá dependencia de datos previos:
   - los tests crean sus recursos.
   - los tests limpian lo que crean.

4. Documentá variables de entorno requeridas en este README.
5. Mantené los e2e pocos y con foco (flujos críticos), el resto va en unit/integration.

## 🆘 Troubleshooting

- **Los e2e fallan por dependencias** → entorno incompleto → verificar servicios (DB/Redis/worker/storage) y settings/keys.
- **Los e2e son inestables** → orden-dependencia o datos compartidos → aislar por test y limpiar recursos.
- **Timeouts** → infra lenta o servicios no listos → agregar waits explícitos y healthchecks en compose.

## 🔎 Ver también

- `../README.md` (índice de tests)
- `../integration/README.md` (componentes con DB real)
- `../unit/README.md` (aislamiento y dobles)
