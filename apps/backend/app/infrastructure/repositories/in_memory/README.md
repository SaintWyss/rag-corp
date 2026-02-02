# Infra: In-Memory Repositories

## 🎯 Misión

Implementaciones volátiles de los repositorios para **Tests Unitarios** y desarrollo rápido sin Docker.
Guardan los datos en diccionarios de Python (`dict`).

**Qué SÍ hace:**

- Simula persistencia (Create, Read, Update, Delete).
- Simula búsqueda vectorial (usando fuerza bruta o librerías simples).
- Se resetea al reiniciar la app.

**Qué NO hace:**

- No persiste datos en disco.
- No soporta concurrencia real (thread-safety limitada).

**Analogía:**
Es un bloc de notas temporal. Sirve para probar ideas rápido, pero si cierras el cuaderno, se borra todo.

## 🗺️ Mapa del territorio

| Recurso                  | Tipo       | Responsabilidad (en humano)           |
| :----------------------- | :--------- | :------------------------------------ |
| `audit_repository.py`    | 🐍 Archivo | Simulación de auditoría.              |
| `conversation.py`        | 🐍 Archivo | Simulación de almacenamiento de chat. |
| `feedback_repository.py` | 🐍 Archivo | Simulación de feedback.               |
| `workspace.py`           | 🐍 Archivo | Simulación de workspaces.             |
| `workspace_acl.py`       | 🐍 Archivo | Simulación de ACLs.                   |

(Y otros archivos de repositorios que se vayan agregando).

## ⚙️ ¿Cómo funciona por dentro?

Usa diccionarios globales o de instancia:

```python
self._store = {}  # {id: Entity}
```

Para búsqueda vectorial, calcula similitud de coseno en memoria (numpy o pure python).

## 🔗 Conexiones y roles

- **Rol Arquitectónico:** Test/Mock Infrastructure.
- **Usado por:** `tests/unit/` y entorno local si `DATABASE_URL` no está set.

## 👩‍💻 Guía de uso (Snippets)

### Resetear estado (para tests)

```python
repo = InMemoryDocumentRepository()
repo.clear()  # Método custom para tests
```

## 🧩 Cómo extender sin romper nada

1.  **Paridad:** Si agregas un método en PostgreSQL, **DEBES** agregarlo aquí también para mantener la interfaz compatible.

## 🔎 Ver también

- [Capa de Tests](../../../../tests/README.md)
