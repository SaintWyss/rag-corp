# HTTP Schemas (DTOs)

Este directorio contiene los **Data Transfer Objects** (DTOs) definidos con Pydantic.
Definen el **Contrato de la API**.

## 🎯 Propósito

Separar la estructura de datos pública (API) de la estructura interna (Dominio).
Esto permite:

- Ocultar campos internos (ej: `password_hash`, `internal_metadata`).
- Formatear datos para el cliente (ej: fechas ISO, camelCase si fuese necesario).
- Validar entradas estrictamente antes de que toquen el dominio.

## 🗂 Estructura

Sigue la misma nomenclatura que los routers:

- `workspaces.py` → Schemas para `/workspaces`
- `documents.py` → Schemas para `/documents`
- `query.py` → Schemas para `/query` y `/ask`

## 📝 Convenciones de Nombramiento

| Sufijo  | Uso                    | Ejemplo                                |
| :------ | :--------------------- | :------------------------------------- |
| `Req`   | Request Body (Entrada) | `CreateWorkspaceReq`, `IngestBatchReq` |
| `Res`   | Response Body (Salida) | `WorkspaceRes`, `DocumentDetailRes`    |
| `Query` | Query Params (Filtros) | `DocumentsListQuery`                   |

## 🛡️ Guidelines

### Validaciones

Usa `@field_validator` para reglas sintácticas (trim, rangos, formatos).
Las reglas de negocio complejas (ej: "nombre único") pertenecen al Caso de Uso, no aquí.

### Types

Usa `UUID` de Python stdlib, Pydantic lo serializa automáticamente a string.
Usa `datetime` con timezone (UTC).

### Annotated

Preferimos `Annotated[str, Field(...)]` (estilo Pydantic v2) para mayor claridad.
