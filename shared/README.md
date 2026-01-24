# shared/ — README

> **Navegación:** [← Volver a raíz del repo](../README.md)

## TL;DR (30 segundos)

- **Qué es:** Código y definiciones compartidas entre Backend y Frontend.
- **Para qué sirve:** Mantener un "contrato" único entre ambas partes — tipos, schemas, interfaces.
- **Quién la usa:** Frontend importa tipos generados, Backend exporta OpenAPI.
- **Impacto si se borra:** Frontend pierde type-safety, hay que definir tipos manualmente y rezar que coincidan con el backend.

---

## Para alguien con 0 conocimientos

### ¿Qué problema resuelve?

Imaginate que el backend dice "un usuario tiene `email`" pero el frontend espera `mail`. Boom, bug en producción.

Esta carpeta contiene la **fuente de verdad** que ambos comparten:
1. El backend genera un archivo `openapi.json` que describe toda su API
2. Una herramienta (`orval`) lee ese JSON y genera código TypeScript
3. El frontend importa ese código generado → siempre están sincronizados

**Analogía:** Es como un diccionario compartido. Si el backend cambia una palabra, el diccionario se actualiza, y el frontend lo ve inmediatamente.

### ¿Qué hay acá adentro?

```
shared/
└── contracts/              # El "contrato" entre FE y BE
    ├── openapi.json        # Esquema de la API (generado por backend)
    ├── orval.config.ts     # Configuración del generador
    ├── package.json        # Define paquete @contracts
    └── src/
        └── generated.ts    # Tipos TypeScript generados
```

| Archivo | Generado por | Usado por |
|---------|--------------|-----------|
| `openapi.json` | Backend (Python) | Orval |
| `generated.ts` | Orval | Frontend (TypeScript) |

### ¿Cómo se usa paso a paso?

**Actualizar contratos después de cambiar el backend:**
```bash
# 1. Exportar OpenAPI desde backend
pnpm contracts:export

# 2. Generar tipos TypeScript
pnpm contracts:gen

# 3. El frontend ya puede usar los tipos nuevos
```

**En el frontend, importar tipos:**
```typescript
import { UserRes, WorkspaceRes } from "@contracts/src/generated";
```

---

## Para engineers / seniors

### Responsabilidades (SRP)

Esta carpeta DEBE contener:
- Esquemas de contrato (OpenAPI, JSON Schema)
- Código generado a partir de esos esquemas
- Configuración de generadores (orval, etc.)

Esta carpeta NO DEBE contener:
- Lógica de negocio
- Implementaciones de API
- Tests
- Utilidades genéricas (eso va en `apps/*/src/utils`)

### Colaboradores y dependencias

| Componente | Rol |
|------------|-----|
| `apps/backend/scripts/export_openapi.py` | Genera `openapi.json` |
| `orval` (tool) | Lee OpenAPI y genera TypeScript |
| `apps/frontend` | Importa `@contracts/src/generated` |
| `pnpm-workspace.yaml` | Incluye `shared/*` como workspace |

### Contratos / Interfaces

**OpenAPI spec (`openapi.json`):**
- Generado automáticamente desde FastAPI
- ~388KB con todos los endpoints
- Incluye schemas de request/response

**TypeScript types (`generated.ts`):**
- ~210KB de tipos generados
- Incluye todos los modelos: User, Workspace, Document, etc.
- Incluye types de request/response para cada endpoint

### Flujo de trabajo típico

**"Agregué un campo nuevo en el backend":**
1. Modificar el modelo Pydantic en backend
2. Correr `pnpm contracts:export`
3. Correr `pnpm contracts:gen`
4. TypeScript te muestra errores donde falta el nuevo campo
5. Actualizar el frontend
6. Commit todo junto

**"El frontend tiene un error de tipos":**
1. Verificar que `openapi.json` esté actualizado
2. Correr `pnpm contracts:gen` por si acaso
3. Si persiste, hay drift — alguien modificó el backend sin actualizar contratos

### Riesgos y pitfalls

| Riesgo | Causa | Detección | Solución |
|--------|-------|-----------|----------|
| Tipos desactualizados | Olvidar correr contracts:gen | Error de tipos en FE | CI incluye check de drift |
| OpenAPI no refleja realidad | Modelo Pydantic mal anotado | Diferencia en runtime | Revisar decoradores de FastAPI |
| Import circular | Mal diseño de tipos | Error de build | Reestructurar dependencias |

### CI Check

El CI verifica drift de contratos:
```yaml
# .github/workflows/ci.yml → contracts-check job
- run: pnpm contracts:export
- run: pnpm contracts:gen
- run: git diff --exit-code shared/contracts/
```
Si hay diferencias, el CI falla → obliga a commitear contratos actualizados.

---

## CRC (Component/Folder CRC Card)

**Name:** `shared/`

**Responsibilities:**
1. Almacenar esquema OpenAPI del backend
2. Generar tipos TypeScript para el frontend
3. Mantener sincronía BE ↔ FE

**Collaborators:**
- Backend (genera OpenAPI)
- Orval (genera TypeScript)
- Frontend (consume tipos)
- CI (verifica sincronía)

**Constraints:**
- Nunca editar `generated.ts` manualmente
- Siempre regenerar después de cambios en backend
- CI debe verificar drift

---

## Evidencia

- `pnpm-workspace.yaml:3` — `shared/*` incluido como workspace
- `shared/contracts/orval.config.ts` — configuración de generación
- `.github/workflows/ci.yml:104-127` — job `contracts-check`
- `package.json:17` — script `contracts:export`
- `package.json:19` — script `contracts:gen`

---

## FAQ rápido

**¿Puedo editar `generated.ts`?**
NO. Se sobrescribe cada vez que corrés `contracts:gen`. Editar `openapi.json` (via backend) es la forma correcta.

**¿Por qué es un paquete npm separado?**
Para poder importar como `@contracts/...` desde el frontend sin paths relativos feos.

**¿Qué pasa si no corro contracts:gen?**
El frontend usará tipos viejos. Puede funcionar, o romper en runtime si los tipos cambiaron.

---

## Glosario

| Término | Definición |
|---------|------------|
| **OpenAPI** | Estándar para describir APIs REST |
| **Orval** | Herramienta que genera código de cliente a partir de OpenAPI |
| **Contract** | Acuerdo formal sobre la interfaz entre sistemas |
| **Drift** | Cuando dos cosas que deberían estar sincronizadas se desalinean |
| **Type-safe** | Que el compilador verifica tipos en tiempo de build |
| **Workspace** | En pnpm/npm, un sub-paquete dentro del monorepo |

---

## Índice de subcarpetas

- [contracts/](./contracts/README.md) — Contrato API (OpenAPI + tipos generados)
