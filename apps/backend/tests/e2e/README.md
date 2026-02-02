# Tests E2E

## 🎯 Misión
Reservar el espacio para pruebas end‑to‑end completas del backend contra un entorno real.

**Qué SÍ hace**
- Define el lugar y la convención para tests e2e.
- Permite ejecutar suites completas cuando estén disponibles.

**Qué NO hace**
- No contiene tests e2e en este momento.
- No reemplaza integración ni unit tests.

**Analogía (opcional)**
- Es la “pista de pruebas” lista para cuando se necesite.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :--- | :--- | :--- |
| 🐍 `__init__.py` | Archivo Python | Marca el paquete e2e. |
| 📄 `README.md` | Documento | Esta documentación. |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output:
- **Input**: `pytest tests/e2e`.
- **Proceso**: (cuando existan) tests ejecutan flujos completos.
- **Output**: validación end‑to‑end.

Tecnologías/librerías usadas aquí:
- pytest.

## 🔗 Conexiones y roles
- Rol arquitectónico: Tests (e2e).
- Recibe órdenes de: desarrolladores/CI.
- Llama a: entorno real con DB/colas/LLMs configurados.
- Contratos y límites: requiere infraestructura completa disponible.

## 👩‍💻 Guía de uso (Snippets)
```python
import pytest

pytest.main(["-v", "tests/e2e"])
```

## 🧩 Cómo extender sin romper nada
- Crea tests e2e con fixtures que levanten entorno real.
- Evita depender de datos previos (setup/teardown).
- Documenta variables de entorno requeridas aquí.

## 🆘 Troubleshooting
- Síntoma: tests e2e fallan por dependencias → Causa probable: entorno incompleto → Verificar DB/Redis/LLM.

## 🔎 Ver también
- [Tests root](../README.md)
- [Integration tests](../integration/README.md)
