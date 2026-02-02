# Tests Unitarios

## 🎯 Misión
Validar comportamientos individuales de módulos y servicios del backend sin dependencias externas reales.

**Qué SÍ hace**
- Prueba funciones/clases en aislamiento.
- Usa mocks/fakes definidos en fixtures.
- Corre rápido y con cobertura enfocada.

**Qué NO hace**
- No requiere DB real ni servicios externos.
- No prueba flujos end‑to‑end.

**Analogía (opcional)**
- Es el “microscopio” que mira piezas individuales.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :--- | :--- | :--- |
| 🐍 `__init__.py` | Archivo Python | Marca el paquete de tests unitarios. |
| 📁 `api/` | Carpeta | Tests unitarios de capa API. |
| 📁 `application/` | Carpeta | Tests unitarios de use cases y servicios. |
| 📁 `domain/` | Carpeta | Tests unitarios de dominio. |
| 📁 `identity/` | Carpeta | Tests unitarios de auth/roles. |
| 📁 `infrastructure/` | Carpeta | Tests unitarios de adapters (fakes). |
| 📄 `README.md` | Documento | Esta documentación. |
| 📁 `worker/` | Carpeta | Tests unitarios de worker y jobs. |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output:
- **Input**: `pytest tests/unit`.
- **Proceso**: fixtures mockean dependencias externas.
- **Output**: resultados rápidos y deterministas.

Tecnologías/librerías usadas aquí:
- pytest, unittest.mock.

## 🔗 Conexiones y roles
- Rol arquitectónico: Tests (unit).
- Recibe órdenes de: desarrolladores/CI.
- Llama a: módulos de `app/` con mocks.
- Contratos y límites: no tocar DB/Redis/S3 reales.

## 👩‍💻 Guía de uso (Snippets)
```python
import pytest

pytest.main(["-v", "tests/unit", "-m", "unit"])
```

## 🧩 Cómo extender sin romper nada
- Escribe tests pequeños y específicos.
- Mockea puertos del dominio con `Mock`.
- Reutiliza fixtures de `tests/conftest.py`.
- Mantén los tests rápidos (sin I/O real).

## 🆘 Troubleshooting
- Síntoma: tests lentos → Causa probable: I/O real accidental → Revisar mocks.
- Síntoma: fixtures no encontrados → Causa probable: import path → Revisar `tests/conftest.py`.

## 🔎 Ver también
- [Tests root](../README.md)
- [Integration tests](../integration/README.md)
