# shared/contracts/ — README

> **Navegación:** [← Volver a shared/](../README.md) · [← Volver a raíz](../../README.md)

## TL;DR (30 segundos)

- **Qué es:** Paquete npm `@contracts` con el esquema OpenAPI y tipos TypeScript generados.
- **Para qué sirve:** Que el frontend tenga tipos exactos de lo que el backend devuelve.
- **Quién la usa:** Frontend importa tipos, CI verifica sincronía.
- **Impacto si se borra:** Frontend pierde autocompletado y type-safety; bugs en runtime.

---

## Para alguien con 0 conocimientos

### ¿Qué problema resuelve?

Cuando escribís código en TypeScript, el editor te ayuda con autocompletado y errores. Pero para eso necesita saber los "tipos" — qué forma tiene cada objeto.

Este paquete contiene tipos **generados automáticamente** desde el backend. Así:
- El backend dice: "un User tiene `id`, `email`, `role`"
- Este paquete lo convierte a TypeScript
- El frontend lo importa y tiene autocompletado perfecto

### ¿Qué hay acá adentro?

```
contracts/
├── openapi.json       # 388KB - Descripción completa de la API
├── orval.config.ts    # Configuración del generador
├── package.json       # Define el paquete @contracts
└── src/
    └── generated.ts   # 210KB - Tipos TypeScript generados
```

| Archivo | Tamaño | Descripción |
|---------|--------|-------------|
| `openapi.json` | 388KB | Todos los endpoints y schemas del backend |
| `generated.ts` | 210KB | Tipos TypeScript para el frontend |

### ¿Cómo se usa paso a paso?

**En el frontend:**
```typescript
// Importar tipos
import type { 
  UserRes, 
  WorkspaceRes, 
  DocumentDetailRes 
} from "@contracts/src/generated";

// Usarlos
const user: UserRes = await api.getCurrentUser();
console.log(user.email); // ✅ Autocompletado funciona
console.log(user.mail);  // ❌ Error de TypeScript
```

**Regenerar después de cambios en backend:**
```bash
# Desde la raíz del repo
pnpm contracts:export  # Actualiza openapi.json
pnpm contracts:gen     # Actualiza generated.ts
```

---

## Para engineers / seniors

### Responsabilidades (SRP)

Este paquete DEBE contener:
- `openapi.json` — schema exportado del backend
- `generated.ts` — tipos generados por Orval
- Configuración de Orval

Este paquete NO DEBE contener:
- Implementaciones de fetch/cliente (eso va en `apps/frontend/src/shared/api`)
- Validadores runtime
- Mocks

### Configuración de Orval

```typescript
// orval.config.ts
export default defineConfig({
  rag: {
    input: "./openapi.json",
    output: {
      mode: "single",           // Un archivo de salida
      target: "./src/generated.ts",
      client: "fetch",          // Genera con fetch API
      clean: true               // Limpia antes de generar
    }
  }
});
```

### Colaboradores y dependencias

| Quién | Cómo interactúa |
|-------|-----------------|
| `apps/backend/scripts/export_openapi.py` | Escribe `openapi.json` |
| `pnpm contracts:export` | Ejecuta export_openapi.py |
| `pnpm contracts:gen` | Ejecuta orval |
| `apps/frontend/src/shared/api/api.ts` | Importa tipos de `@contracts` |

### Tipos principales generados

| Tipo | Descripción |
|------|-------------|
| `UserRes` | Respuesta de /auth/me |
| `WorkspaceRes` | Un workspace |
| `WorkspacesListRes` | Lista de workspaces |
| `DocumentDetailRes` | Detalle de documento |
| `DocumentSummaryRes` | Resumen de documento |
| `QueryReq` / `QueryRes` | Request/response de /query |
| `IngestTextReq` / `IngestTextRes` | Ingesta de texto |

### Flujo de trabajo típico

**"Agregué un endpoint nuevo en backend":**
1. Crear el endpoint en FastAPI con tipos Pydantic
2. `pnpm contracts:export`
3. `pnpm contracts:gen`
4. Importar el nuevo tipo en frontend
5. Commit los 3 archivos: backend, openapi.json, generated.ts

**"TypeScript dice que un campo no existe":**
1. ¿El campo está en el backend? → Verificar modelo Pydantic
2. ¿`openapi.json` lo tiene? → Si no, correr `contracts:export`
3. ¿`generated.ts` lo tiene? → Si no, correr `contracts:gen`
4. ¿Persiste? → Puede ser cache de TypeScript, reiniciar IDE

### Riesgos y pitfalls

| Riesgo | Causa | Solución |
|--------|-------|----------|
| `generated.ts` desactualizado | Olvidar regenerar | CI verifica drift |
| Import no funciona | Path alias mal configurado | Verificar tsconfig paths |
| Tipos no coinciden con runtime | OpenAPI mal generado | Verificar decoradores FastAPI |
| `openapi.json` muy grande | Muchos endpoints | Es normal (~388KB) |

### CI Check de Drift

```yaml
# .github/workflows/ci.yml
contracts-check:
  steps:
    - run: pnpm contracts:export
    - run: pnpm contracts:gen
    - run: git diff --exit-code shared/contracts/
```

Si hay diferencias → CI falla → obliga a commitear contratos actualizados.

---

## CRC (Component/Folder CRC Card)

**Name:** `shared/contracts/`

**Responsibilities:**
1. Almacenar esquema OpenAPI del backend
2. Contener tipos TypeScript generados
3. Servir como paquete importable `@contracts`

**Collaborators:**
- Backend export script
- Orval generator
- Frontend imports
- CI drift check

**Constraints:**
- `generated.ts` NUNCA debe editarse manualmente
- `openapi.json` solo debe modificarse via export
- Siempre commitear ambos archivos juntos

---

## Evidencia

- `shared/contracts/package.json:2` — nombre `@contracts`
- `shared/contracts/orval.config.ts:5-10` — config de generación
- `apps/frontend/src/shared/api/api.ts:2-18` — imports de `@contracts/src/generated`
- `package.json:17,19` — scripts `contracts:export` y `contracts:gen`

---

## FAQ rápido

**¿Por qué 210KB de tipos?**
Porque describe TODOS los endpoints del backend. Es normal para una API completa.

**¿Puedo agregar tipos custom?**
Mejor no. Si necesitás tipos extra, extendé los generados en el frontend:
```typescript
import type { UserRes } from "@contracts/src/generated";
type UserWithExtras = UserRes & { customField: string };
```

**¿Qué es Orval?**
Una herramienta que lee OpenAPI y genera código de cliente. Similar a OpenAPI Generator pero mejor para TypeScript.

**¿Por qué no usar OpenAPI Generator directamente?**
Orval genera código más limpio y tiene mejor soporte para TypeScript moderno.

---

## Glosario

| Término | Definición |
|---------|------------|
| **OpenAPI** | Especificación para describir APIs REST |
| **Schema** | Definición de la estructura de datos |
| **Orval** | Generador de código TypeScript desde OpenAPI |
| **Type-safe** | Verificación de tipos en compile-time |
| **Drift** | Desincronización entre código y especificación |
