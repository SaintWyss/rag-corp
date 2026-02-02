# Interface: HTTP (FastAPI Layer)

## 🎯 Misión

Implementación concreta de la API REST usando **FastAPI**.
Aquí se definen las rutas, se validan los payloads JSON (`Schemas`) y se inyectan las dependencias (`Dependencies`).

**Qué SÍ hace:**

- Rutas (`routers/`).
- Schemas Pydantic de entrada/salida (`schemas/`).
- Extracción de parámetros (Query, Path, Body).
- Transformación de excepciones de dominio a códigos HTTP (`error_mapping.py`).

**Qué NO hace:**

- **NUNCA** ejecuta lógica de negocio en el controlador. Solo debe llamar al Use Case.

**Analogía:**
Es el Recepcionista del Hotel. Recibe al huésped, verifica su reserva (Auth), y llama al botones (Use Case) para que lleve las maletas.

## 🗺️ Mapa del territorio

| Recurso            | Tipo       | Responsabilidad (en humano)                                            |
| :----------------- | :--------- | :--------------------------------------------------------------------- |
| `dependencies.py`  | 🐍 Archivo | `Depends(get_current_user)` y otras inyecciones de FastAPI.            |
| `error_mapping.py` | 🐍 Archivo | Mapeo `DomainException` -> `HTTPException`.                            |
| `router.py`        | 🐍 Archivo | Utilidad para agrupar routers si fuera necesario.                      |
| `routers/`         | 📁 Carpeta | **Controladores**. Archivos con los `@router.get(...)`.                |
| `routes.py`        | 🐍 Archivo | **Router Principal**. Agrupa todos los sub-routers (`/chat`, `/docs`). |
| `schemas/`         | 📁 Carpeta | **DTOs**. Modelos Pydantic (`BaseModel`) para request/response.        |

## ⚙️ ¿Cómo funciona por dentro?

1.  **Request:** Llega a un endpoint en `routers/`.
2.  **Dependency Injection:** `dependencies.py` resuelve el usuario actual y los repositorios necesarios (usando `app.container`).
3.  **Use Case:** Se instancia el Use Case y se ejecuta.
4.  **Response:** El resultado se valida contra un Schema de salida.

## 🔗 Conexiones y roles

- **Rol Arquitectónico:** Interface Adapter (HTTP).
- **Recibe órdenes de:** `app.api.main` (que monta este router).
- **Llama a:** `app.application`.

## 👩‍💻 Guía de uso (Snippets)

### endpoint típico

```python
@router.post("/items", response_model=ItemOutput)
def create_item(
    payload: CreateItemInput,
    use_case: CreateItemUseCase = Depends(get_create_item_use_case)
):
    return use_case.execute(payload)
```

## 🧩 Cómo extender sin romper nada

1.  **Nuevo Endpoint:** Crea el método en el router correspondiente.
2.  **Docs:** Usa `summary`, `description` y `response_model` en el decorador para que Swagger UI quede perfecto.

## 🆘 Troubleshooting

- **Síntoma:** Error 422 Unprocessable Entity.
  - **Causa:** El JSON envíado no coincide con el Schema Pydantic.
- **Síntoma:** El endpoint devuelve un objeto ORM en vez de JSON.
  - **Causa:** Olvidaste definir `response_model` o el objeto de dominio no es serializable.

## 🔎 Ver también

- [Routers (Controladores)](./routers/README.md)
- [Schemas (DTOs)](./schemas/README.md)
