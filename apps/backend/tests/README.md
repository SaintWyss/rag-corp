# Layer: Tests Hub

## 🎯 Misión

Esta carpeta contiene toda la estrategia de aseguramiento de calidad (QA) automatizada del backend.
Sigue la **Pirámide de Tests**: muchos unitarios en la base, algunos de integración en el medio, y pocos E2E en la punta.

**Qué SÍ hace:**

- Configura el entorno de pruebas (`conftest.py`).
- Define los fixtures compartidos (User, Workspace, DB Session).

**Qué NO hace:**

- No contiene código de producción.

## 🗺️ Mapa del territorio

| Recurso        | Tipo       | Responsabilidad (en humano)                                                     |
| :------------- | :--------- | :------------------------------------------------------------------------------ |
| `conftest.py`  | 🐍 Archivo | **Configuración Global**. Fixtures de Pytest (cliente HTTP, db session).        |
| `e2e/`         | 📁 Carpeta | Tests de punta a punta (Smoke Tests).                                           |
| `integration/` | 📁 Carpeta | Tests con dependencias reales (Postgres, pero con External Services mockeados). |
| `unit/`        | 📁 Carpeta | Tests aislados y rápidos (sin I/O real).                                        |

## ⚙️ ¿Cómo funciona por dentro?

Usamos `pytest` como runner.

- **Unitarios:** Usan `InMemoryDocumentRepository` para velocidad.
- **Integración:** Encienden el contenedor de DB real (o usan el servicio de docker-compose) y limpian tablas entre tests.

## 🔗 Conexiones y roles

- **Rol Arquitectónico:** Quality Assurance.
- **Importa:** Todo el código de `app`.

## 👩‍💻 Guía de uso (Snippets)

### Correr todo

```bash
pytest
```

### Correr solo unitarios (rápido)

```bash
pytest tests/unit
```

## 🧩 Cómo extender sin romper nada

1.  **Fixtures:** Si creas una nueva entidad compleja, crea un fixture `factory` en `conftest.py` para reutilizar.

## 🔎 Ver también

- [Tests Unitarios](./unit/README.md)
- [Tests Integración](./integration/README.md)
