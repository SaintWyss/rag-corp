# Feature: Workspace Management

## 🎯 Misión

Gestiona los **Espacios de Trabajo (Workspaces)**, que son los contenedores lógicos de documentos y usuarios.
Define los límites de aislamiento: documentos en el Workspace A no deben verse en el Workspace B.

**Qué SÍ hace:**

- CRUD de Workspaces (Crear, Editar, Archivar).
- Gestión de acceso (quién puede ver este workspace).
- Publicación de workspaces (hacerlos visibles a la organización).

**Qué NO hace:**

- No gestiona documentos dentro (eso es `usecases/documents`).

## 🗺️ Mapa del territorio

| Recurso                | Tipo       | Responsabilidad (en humano)                         |
| :--------------------- | :--------- | :-------------------------------------------------- |
| `archive_workspace.py` | 🐍 Archivo | Soft-delete de un workspace (papelera).             |
| `create_workspace.py`  | 🐍 Archivo | Crea un nuevo espacio.                              |
| `get_workspace.py`     | 🐍 Archivo | Obtiene detalles de un espacio por ID.              |
| `list_workspaces.py`   | 🐍 Archivo | Lista los espacios visibles para el usuario.        |
| `publish_workspace.py` | 🐍 Archivo | Cambia la visibilidad a pública/org.                |
| `share_workspace.py`   | 🐍 Archivo | Permite compartir workspace con emails específicos. |
| `update_workspace.py`  | 🐍 Archivo | Modifica nombre u opciones.                         |
| `workspace_access.py`  | 🐍 Archivo | Lógica de validación de acceso.                     |
| `workspace_results.py` | 🐍 Archivo | DTOs de salida comunes.                             |

## ⚙️ ¿Cómo funciona por dentro?

El concepto clave es **Visibilidad**:

- **PRIVATE:** Solo el creador (Owner).
- **SHARED:** Creador + usuarios invitados explícitamente (ACL).
- **ORG_READ:** Toda la organización puede leer.

## 🔗 Conexiones y roles

- **Rol Arquitectónico:** Use Cases (Workspace Feature).
- **Colabora con:** `WorkspaceRepository`, `WorkspaceACLRepository`.

## 👩‍💻 Guía de uso (Snippets)

### Crear un workspace

```python
use_case = CreateWorkspaceUseCase(workspace_repo)
ws = use_case.execute(
    name="Finanzas 2024",
    owner_id=user_id
)
```

## 🧩 Cómo extender sin romper nada

1.  **Nuevas reglas de permisos:** Modifica `workspace_access.py`.
2.  **Validaciones:** Si quieres limitar workspaces por usuario, hazlo en `create_workspace.py`.

## 🆘 Troubleshooting

- **Síntoma:** El usuario no ve un workspace compartido.
  - **Causa:** No se agregó la entrada en la tabla ACL. Revisa `share_workspace.py`.

## 🔎 Ver también

- [Use Case Hub](../README.md)
