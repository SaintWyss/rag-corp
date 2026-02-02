# Layer: Use Cases (Actions)

## 🎯 Misión

Este directorio es el **Menú de Opciones** de la aplicación.
Cada carpeta aquí representa una "Feature" o área funcional, y cada archivo dentro representa una "Acción" que el usuario puede realizar.

**Qué SÍ hace:**

- Contiene clases `*UseCase` con un método público `execute()`.
- Define los DTOs de entrada (`*Input`) y salida (`*Output`) si son complejos.
- Aplica reglas de negocio específicas de la acción (ej. "¿Tiene permiso el usuario X para ver el documento Y?").

**Qué NO hace:**

- No implementa persistencia.
- No sabe de HTTP (JSON, Status Codes).

**Analogía:**
Es el menú del restaurante. "Hamburguesa con queso", "Ensalada César". Cada ítem es un Use Case.

## 🗺️ Mapa del territorio

| Recurso      | Tipo       | Responsabilidad (en humano)                                       |
| :----------- | :--------- | :---------------------------------------------------------------- |
| `chat/`      | 📁 Carpeta | Interacciones conversacionales (Preguntar, Historial, Streaming). |
| `documents/` | 📁 Carpeta | Gestión CRUD de documentos (Listar, Borrar, Ver).                 |
| `ingestion/` | 📁 Carpeta | Pipeline de carga y procesamiento (Upload, OCR, Chunking).        |
| `workspace/` | 📁 Carpeta | Gestión de espacios de trabajo (Crear, Compartir, Editar).        |

## ⚙️ ¿Cómo funciona por dentro?

Todos los Use Cases siguen un patrón similar:

1.  **Inyección:** Reciben repositorios y servicios en el `__init__`.
2.  **Validación:** Verifican permisos o reglas de negocio básicas.
3.  **Ejecución:** Orquestan la llamada a repositorios/servicios.
4.  **Retorno:** Devuelven objetos de Dominio o DTOs puros.

## 🔗 Conexiones y roles

- **Rol Arquitectónico:** Application Services (Feature Modules).
- **Recibe órdenes de:** Controladores HTTP (API) y Workers (Background jobs).

## 👩‍💻 Guía de uso (Snippets)

### Estructura típica de un Use Case

```python
class MyUseCase:
    def __init__(self, repo: MyRepository):
        self.repo = repo

    def execute(self, input_data: CreateItemInput) -> Item:
        # 1. Validar
        if input_data.value < 0:
            raise ValueError("Invalid")

        # 2. Orquestar
        item = Item(name=input_data.name)
        self.repo.save(item)

        return item
```

## 🧩 Cómo extender sin romper nada

1.  **Nueva Acción:** Identifica a qué familia pertenece (`chat`, `workspace`). Si no encaja, crea una carpeta nueva.
2.  **Inyección:** Recuerda registrar el nuevo Use Case en `app/container.py` para que la API pueda instanciarlo.

## 🔎 Ver también

- [Chat & RAG](./chat/README.md)
- [Ingesta de Documentos](./ingestion/README.md)
