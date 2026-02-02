# Infra: Repositories Hub

## 🎯 Misión

Contiene las implementaciones concretas de la persistencia de datos.
Aquí se decide **dónde** y **cómo** se guardan las Entidades del Dominio.

**Qué SÍ hace:**

- Agrupa implementaciones por tecnología (`postgres`, `in_memory`).

**Qué NO hace:**

- No define las interfaces (eso está en `domain/repositories.py`).

**Analogía:**
Es el archivador. Puedes tener una carpeta física (`postgres`) o usar tu memoria (`in_memory`), pero ambos cumplen la función de guardar papeles.

## 🗺️ Mapa del territorio

| Recurso      | Tipo       | Responsabilidad (en humano)                                      |
| :----------- | :--------- | :--------------------------------------------------------------- |
| `in_memory/` | 📁 Carpeta | Implementaciones volátiles (Dicts) para tests unitarios rápidos. |
| `postgres/`  | 📁 Carpeta | Implementaciones reales de producción sobre PostgreSQL.          |

## ⚙️ ¿Cómo funciona por dentro?

Todas las clases aquí deben implementar estrictamente los `Protocol` definidos en `app.domain.repositories`.
Si el dominio pide `save(doc)`, ambas implementaciones deben tener ese método.

## 🔗 Conexiones y roles

- **Rol Arquitectónico:** Infrastructure Adapters.
- **Implementa:** Interfaces de `app.domain`.

## 👩‍💻 Guía de uso (Snippets)

### Cambiar de implementación

En `app/container.py`:

```python
# Para producción
repo = PostgresDocumentRepository()

# Para testing local rápido
repo = InMemoryDocumentRepository()
```

## 🧩 Cómo extender sin romper nada

1.  **Nueva Tecnología:** Para agregar soporte a MongoDB, crea `repositories/mongo/` y sigue las mismas interfaces.

## 🔎 Ver también

- [PostgreSQL Repos](./postgres/README.md)
- [In-Memory Repos](./in_memory/README.md)
