# Guía Definitiva de README — Rag Corp (Raíz, Padres y Hojas)

> Objetivo: que **todo el repositorio** sea operable y mantenible sin “memoria tribal”, con una convención única para README **raíz**, **padres (portales)** y **hojas (detalles)**.

---

## 0) Alcance y regla de oro

### Alcance
Esta guía define:
- **Qué tipo de README existe**, qué pregunta responde cada uno y dónde vive.
- **Estructura obligatoria** (secciones) y convenciones de estilo.
- **Reglas de canon vs stub** (anti-duplicación).
- **Modelos listos para copiar/pegar**.

### Regla de oro
**Un README no es “texto”**: es un **manual operativo**.
- Si una sección no ayuda a **operar, mantener o auditar**, se elimina.

---

## 1) Tipos de README (y qué pregunta responden)

### 1.1 README Raíz (repo)
**Ubicación:** `/README.md`

**Responde:**
- ¿Qué es el sistema?
- ¿Qué problema resuelve?
- ¿Cómo lo corro/deployeo?
- ¿Dónde está la fuente de verdad (docs/contrato/runbooks)?
- ¿Qué perfiles/stack existen (backend/frontend/worker/infra)?

**No entra en:** detalles internos de módulos.

---

### 1.2 README Padre (portal / index)
**Ubicación típica:** `README.md` dentro de una carpeta grande (ej.: `apps/backend/README.md`, `apps/frontend/README.md`, `docs/README.md`, `infra/README.md`, `shared/contracts/README.md`).

**Responde:**
- ¿Qué representa esta carpeta en el sistema?
- ¿Cuáles son sus límites e invariantes?
- ¿Cómo me oriento? (rutas rápidas + mapa)
- ¿Cuáles son las hojas relevantes?

**No baja al micro**: no explica la lógica de cada archivo.

---

### 1.3 README Hoja (detalle máximo)
**Ubicación típica:** `README.md` en un submódulo con lógica propia (ej.: `apps/backend/app/infrastructure/parsers/README.md`, `apps/frontend/src/shared/api/README.md`, `apps/backend/app/application/usecases/chat/README.md`).

**Responde:**
- ¿Cómo funciona esto por dentro?
- ¿Cuáles son los contratos/DTOs y errores tipados?
- ¿Qué seguridad/límites se aplican y por qué?
- ¿Cómo lo extiendo sin romper invariantes?
- ¿Cómo se testea y cómo se diagnostica?

---

### 1.4 README Stub (OBSOLETO)
**Ubicación:** donde exista un doc/README histórico que se mantiene por compatibilidad.

**Responde:**
- ¿Por qué esto es obsoleto?
- ¿Cuál es el canon?

**Contenido:** mínimo, sin lógica operativa.

---

## 2) Reglas universales (aplican a TODOS los README)

### 2.1 No llevan Tarjeta CRC
**Regla:** README **no** incluye Tarjeta CRC.
- La CRC es para archivos de implementación/config donde el formato lo permite.

### 2.2 Títulos y tagline (obligatorio)
- Formato: `# <Área> — <Rol>` o `# <Área>`
- Tagline 1 línea en metáfora operativa:
  - “Como una **central de navegación** …”
  - “Como un **router** …”
  - “Como un **orquestador** …”

### 2.3 Rutas rápidas por intención (obligatorio)
Siempre al inicio:
- “Quiero X” → link directo.

### 2.4 Mapa del territorio (obligatorio)
Tabla:
| Recurso | Tipo | Responsabilidad (en humano) |

- En README padre: tabla corta.
- En README hoja: tabla completa.

### 2.5 Troubleshooting (obligatorio)
Formato: **síntoma → causa probable → dónde mirar → solución**.

### 2.6 Lenguaje
- Español claro, técnico, concreto.
- Hablar en términos de **responsabilidades, límites, invariantes, contratos**.
- Evitar “marketing” interno, relleno o adjetivos sin evidencia.

### 2.7 Anti-duplicación (canon vs stub)
- Si algo ya está definido en una fuente canónica (OpenAPI, `docs/reference/*`, runbooks), el README **linkea**: no lo copia.

---

## 3) Fuente de verdad (anti-drift) — regla de enlace

Cuando un README describa “cómo funciona”, debe incluir al menos una evidencia:
- Link a contrato (OpenAPI).
- Link a runtime (compose/k8s/Dockerfile).
- Link a tests relevantes.
- Link a código responsable.

**Orden de prioridad ante contradicciones:**
1) OpenAPI / contratos
2) Runtime (compose/k8s/config)
3) Arquitectura + ADRs
4) Referencia técnica (docs/reference)
5) Portales/índices

---

## 4) Convención del árbol (cuándo crear README)

### 4.1 Reglas prácticas
- Cada carpeta “grande” tiene README **padre**.
- Cada submódulo con lógica propia tiene README **hoja**.
- Los padres **siempre linkean** a hojas.

### 4.2 Señales de que un submódulo necesita README hoja
- Tiene estrategias/registries/adaptadores.
- Tiene límites de seguridad/performance que deben mantenerse.
- Tiene contratos/DTOs/errores tipados propios.
- Tiene tests dedicados.

### 4.3 Señales de que NO hace falta README hoja
- Carpeta sólo de re-exports (`index.ts`) o tipos triviales.
- Carpeta sin lógica (assets, estilos simples) — puede documentarse en el padre.

---

## 5) Modelo de README Raíz (repo) — plantilla CANON

```md
# RAG Corp — Plataforma de conocimiento documental por Workspaces
> Como una **central de conocimiento operable**: convierte documentación en respuestas con evidencia, con aislamiento y control de acceso por workspace.

## Misión
RAG Corp centraliza documentos, los procesa (texto → fragmentos → búsqueda semántica) y habilita **consulta/answering con fuentes**, bajo **scoping estricto por workspaces**.

- Qué resuelve:
  - Reduce tiempo de búsqueda y dependencia de conocimiento informal.
  - Aporta trazabilidad: respuestas con evidencia (fuentes/citas).
  - Refuerza seguridad: aislamiento por workspace + permisos.

- Qué no resuelve (y por qué):
  - No reemplaza políticas de clasificación DLP avanzadas. Razón: alcance. Consecuencia: se recomienda integrar controles adicionales si aplica.

## Si venís con una intención concreta (rutas rápidas)
- Quiero entender arquitectura → `docs/architecture/overview.md`
- Quiero operar/deploy → `docs/runbook/deploy.md` + `docs/runbook/production-hardening.md`
- Quiero integrar por API → `shared/contracts/openapi.json`
- Quiero ver permisos/scoping → `docs/reference/access-control.md`
- Quiero límites/timeouts → `docs/reference/limits.md`
- Quiero troubleshooting → `docs/runbook/troubleshooting.md`

## Quickstart (local)
> Canon: `docs/runbook/local-dev.md`

## Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :-- | :-- | :-- |
| `apps/backend/` | Servicio | API + dominio + use cases + adaptadores |
| `apps/frontend/` | UI | Interfaz web (Next.js) |
| `shared/contracts/` | Contratos | OpenAPI y generación de clientes |
| `infra/` | Infra | k8s, Prometheus/Grafana, provisioning |
| `docs/` | Docs | Portales, referencia técnica y runbooks |

## Operación
- Salud, métricas y runbooks → `docs/runbook/`

## Seguridad
- Hardening y políticas → `docs/security/`

## Contribución
- Reglas de contribución → `docs/project/CONTRIBUTING.md`

## Troubleshooting
Síntoma: <...>
Causa probable: <...>
Dónde mirar: <...>
Solución: <...>
```

---

## 6) Modelo de README Padre (portal) — plantilla CANON

```md
# <Nombre del área> — <Tagline humano>
> Como una **<central/puerta/router>**: <qué hace en humano>.

## Misión
Este directorio es la **unidad <rol>** de RAG Corp. Desde acá se <organiza/ejecuta/define> <X>.
El código/implementación de <Y> vive en `<ruta>`, mientras que acá se mantiene <Z>.

- Qué resuelve:
  - <1–3 bullets>
- Qué no resuelve (y por qué):
  - No hace <X>. Razón: <razón>. Consecuencia: <impacto>.

## Si venís con una intención concreta (rutas rápidas)
- Punto de entrada principal → `./<archivo>`
- Configuración y envs → `./<doc o ruta>`
- Arquitectura y límites → `./<subarea>/README.md`
- Tests → `./<tests>/README.md`
- Troubleshooting → `./<doc>`

## Qué SÍ hace
- <bullet>
- <bullet>

## Qué NO hace (y por qué)
- No hace <X>. Razón: <razón>. Consecuencia: <impacto práctico>.

## Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :-- | :-- | :-- |
| `<archivo/carpeta>` | `<tipo>` | `<qué aporta>` |
| `<archivo/carpeta>` | `<tipo>` | `<qué aporta>` |

## Arquitectura del área (límites y dependencias)
### Rol arquitectónico
- Rol: <router root / feature module / infra adapter / ui kit / tooling>

### Reglas de límites (imports/dependencias)
- Puede importar: <...>
- No puede importar: <...>
- Regla fuerte: <en 1–2 líneas>

### Invariantes (cosas que no se rompen)
- Invariante 1: <...>
- Invariante 2: <...>

## ¿Cómo funciona por dentro?
- **Input:** <...>
- **Proceso:** <...>
- **Output:** <...>

## Guía de uso (Snippets)
```bash
# comando operativo típico
```

## Cómo extender sin romper nada
Paso 1: <qué tocar>
Paso 2: <dónde cablear>
Paso 3: <qué tests agregar>
Invariantes a respetar: <...>

## Troubleshooting
Síntoma: <...>
Causa probable: <...>
Dónde mirar: <...>
Solución: <...>

## Ver también (Índice de hojas)
- `./<subarea>/README.md` — <qué explica>
- `./<subarea>/README.md` — <qué explica>
```

---

## 7) Modelo de README Hoja (detalle máximo) — plantilla CANON

```md
# <Nombre del submódulo>
> Como un **<lector/puente/filtro/orquestador>**: <qué hace en humano>.

## Misión
Este módulo implementa <X> a través de <estrategias/puertos/adaptadores>.
Resuelve: <lista corta>. Mantiene invariantes: <lista corta>.

- Punto de entrada: `<archivo>`
- Contratos/DTOs: `<archivo>`
- Errores tipados: `<archivo>`

## Recorridos rápidos por intención
- **Quiero ver el punto de entrada** → `<archivo>`
- **Quiero ver selección/estrategia** → `<archivo>`
- **Quiero ver normalización/límites** → `<archivo>`
- **Quiero ver errores y contratos** → `<archivo>`
- **Quiero ver ejemplos de uso** → sección “Guía de uso”

## Qué SÍ hace
- <bullet>
- <bullet>

## Qué NO hace (y por qué)
- No hace <X>. Razón: <razón>. Impacto: <impacto>.

## Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :-- | :-- | :-- |
| `<archivo>` | Archivo | <...> |
| `<carpeta>` | Carpeta | <...> |

## ¿Cómo funciona por dentro? (paso a paso)
### 1) Entrada principal: `<punto_de_entrada>`
- **Input:** <...>
- **Proceso:**
  1. <...>
  2. <...>
- **Output:** <...>

### 2) Estrategias / Registry / Selección (si aplica)
- **Input:** <...>
- **Proceso:** <...>
- **Output:** <...>

### 3) Errores y contratos (tipado)
- Errores:
  - `<ErrorA>`: <qué significa>
- Contratos/DTOs:
  - `<ContratoA>`: <qué contiene>

## Seguridad y límites defensivos
- Validaciones: <...>
- Límites: <...>
- Mitigaciones: <...>
- No confiar en: <...>

## Performance
- Timeouts/Abort: <...>
- Evitar trabajo innecesario: <...>
- Caching (si aplica): <...>

## Conexiones y roles
- Rol arquitectónico: <...>
- Recibe órdenes de: <...>
- Llama a: <...>
- Reglas de límites: <...>

## Guía de uso (Snippets)
```ts
// ejemplo mínimo real
```

## Cómo extender sin romper nada
1) Crear <nuevo componente>
2) Registrar en <lugar>
3) Agregar tests en <path>
4) Respetar invariantes: <...>

## Checklist de calidad (DoD del submódulo)
- [ ] CRC en archivos (excepto README/JSON)
- [ ] Tipos estrictos y APIs pequeñas
- [ ] Errores tipados/normalizados
- [ ] Seguridad revisada
- [ ] Performance revisada
- [ ] Tests ajustados
- [ ] No rompe boundaries
- [ ] Docs actualizadas

## Troubleshooting
Síntoma: <...>
Causa probable: <...>
Dónde mirar: <...>
Solución: <...>

## Ver también
- `../README.md` (padre)
- `../../<otra area>/README.md`
```

---

## 8) Modelo de README Stub (OBSOLETO)

```md
# OBSOLETO — <Nombre>
> Este archivo se mantiene por compatibilidad/histórico. **No es canónico**.

## Motivo
<1–3 líneas: por qué quedó obsoleto (evitar duplicación, drift, etc.)>

## Canon
- Ver: `<ruta_canónica>`

## Nota
No agregar contenido operativo aquí. Actualizar siempre el canon.
```

---

## 9) Checklist global (Definition of Done para README)

### README Raíz
- [ ] Define misión + problema que resuelve
- [ ] Tiene rutas rápidas por intención
- [ ] Mapa del territorio completo
- [ ] Linkea a docs/runbooks/seguridad/contrato
- [ ] Troubleshooting mínimo

### README Padre
- [ ] Tagline + misión + límites
- [ ] Rutas rápidas por intención
- [ ] Mapa del territorio
- [ ] Invariantes + reglas de dependencia
- [ ] Índice de hojas al final
- [ ] Troubleshooting

### README Hoja
- [ ] Punto de entrada, contratos, errores
- [ ] Paso a paso interno
- [ ] Seguridad + límites + performance
- [ ] Cómo extender + checklist DoD del módulo
- [ ] Troubleshooting

---

## 10) Recomendación de aplicación en Rag Corp (árbol sugerido)

### README Raíz
- `/README.md`

### Padres (portales)
- `docs/README.md`
- `apps/README.md` (opcional si `apps/` es grande)
- `apps/backend/README.md`
- `apps/frontend/README.md`
- `infra/README.md`
- `shared/README.md`
- `shared/contracts/README.md`

### Hojas típicas (ejemplos)
- `apps/backend/app/README.md`
- `apps/backend/app/application/usecases/README.md`
- `apps/backend/app/infrastructure/README.md`
- `apps/backend/app/interfaces/api/http/README.md`
- `apps/frontend/src/shared/api/README.md`
- `apps/frontend/src/shared/ui/README.md`
- `apps/frontend/src/features/<feature>/README.md` (si la feature tiene reglas/contratos)

---

**Fin de la guía.**

