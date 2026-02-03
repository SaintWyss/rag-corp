# e2e
Como una **pista de pruebas**: reservada para flujos completos con infraestructura real.

## 🎯 Misión
Este directorio deja el espacio y las convenciones para pruebas end-to-end cuando haya suites completas (API + DB + colas + storage + LLM según configuración).

### Qué SÍ hace
- Define el lugar de los tests e2e.
- Permite que CI/local tengan una ruta estable cuando se agreguen suites.

### Qué NO hace (y por qué)
- No contiene tests e2e por ahora. Razón: no hay casos definidos/estables todavía. Consecuencia: la cobertura actual vive en unit/integration.
- No reemplaza unit/integration. Razón: esos niveles son el gate principal. Consecuencia: e2e complementa, no sustituye.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :-- | :-- | :-- |
| `README.md` | Documento | Guía del nivel e2e. |
| `__init__.py` | Archivo Python | Marca el paquete. |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output.

- **Input:** `pytest tests/e2e`.
- **Proceso:** Pytest ejecutará aquí los flujos end-to-end cuando existan.
- **Output:** validación completa (más lenta, mayor cobertura).

## 🔗 Conexiones y roles
- **Rol arquitectónico:** tests end-to-end.
- **Recibe órdenes de:** desarrolladores/CI.
- **Llama a:** infraestructura real (DB/Redis/storage/LLM) cuando se habilite.
- **Reglas de límites:** evitar dependencias externas no controladas.

## 👩‍💻 Guía de uso (Snippets)
```bash
# Por qué: comando directo para validar el flujo.
cd apps/backend
pytest tests/e2e
```

```python
# Desde Python
import pytest
pytest.main(["-v", "tests/e2e"])
```

## 🧩 Cómo extender sin romper nada
- Definí el entorno real (compose/profile, servicios obligatorios).
- Agregá fixtures e2e con setup/teardown (DB limpia, worker activo).
- Wiring: si necesitás servicios, obtenelos desde `app/container.py`.
- Tests: escribirlos en `apps/backend/tests/e2e/`.

## 🆘 Troubleshooting
- **Síntoma:** tests fallan por dependencias.
- **Causa probable:** entorno incompleto.
- **Dónde mirar:** compose/variables de entorno.
- **Solución:** levantar DB/Redis/worker/storage antes de correr.
- **Síntoma:** flujos inestables.
- **Causa probable:** datos compartidos u orden-dependencia.
- **Dónde mirar:** fixtures e2e.
- **Solución:** aislar por test y limpiar recursos.
- **Síntoma:** timeouts.
- **Causa probable:** infra lenta o servicios no listos.
- **Dónde mirar:** logs y healthchecks.
- **Solución:** agregar waits o healthchecks.
- **Síntoma:** tests vacíos.
- **Causa probable:** no hay casos e2e implementados.
- **Dónde mirar:** este directorio.
- **Solución:** agregar la suite cuando esté definida.

## 🔎 Ver también
- `../README.md`
- `../integration/README.md`
- `../unit/README.md`
