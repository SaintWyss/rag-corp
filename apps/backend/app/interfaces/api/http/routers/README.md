# Routers (Controllers)

Este directorio contiene los controladores HTTP agrupados por **Bounded Context** (Dominio/Funcionalidad).

## 🗂 Organización

Cada archivo representa un bloque funcional cohesivo:

- `workspaces.py`: Gestión de espacios de trabajo, permisos y auditoría.
- `documents.py`: Ciclo de vida de documentos (upload, ingest, delete).
- `query.py`: Motor de búsqueda y RAG (Retrieve & Generate).
- `admin.py`: Endpoints de sistema y monitoreo.

## 🛠 Cómo agregar un nuevo Router

1.  Crear el archivo `mi_feature.py` en este directorio.
2.  Definir `router = APIRouter()`.
3.  Implementar endpoints usando `dependencies.py` para inyectar casos de uso.
4.  Exponer el router en `__init__.py`.
5.  Registrar el router en `../router.py` (el router raíz).

## 📝 Reglas de Juego (Guidelines)

### Inyección de Dependencias

Usa `Depends(get_use_case_factory)` para obtener la lógica de negocio. Nunca instancies servicios manualmente dentro del endpoint.

### Helpers Privados

Si tienes lógica repetitiva de validación HTTP (ej: validar un header específico), crea funciones privadas (`_helper_function`) al inicio del archivo o muévelas a `dependencies.py` si son compartidas.

### Responses

Usa siempre `response_model` con esquemas de `../schemas/`. Evita retornar diccionarios crudos.
