# RAG Corp - Fixes Aplicados

## ✅ Problemas Críticos Corregidos

### 1. **API Key de Google Gemini**

**Problema**: La variable `GOOGLE_API_KEY` estaba vacía en [compose.yaml](compose.yaml).  
**Solución**: Ahora usa `${GOOGLE_API_KEY}` para leer desde el entorno del host.

**Acción requerida**:

```bash
# Crea un archivo .env en la raíz del proyecto
echo "GOOGLE_API_KEY=tu_clave_aqui" > .env
```

---

### 2. **CORS Bloqueando Requests del Frontend**

**Problema**: FastAPI no tenía configuración CORS, bloqueando llamadas desde localhost:3000.  
**Solución**: Agregado middleware CORS en [apps/backend/app/main.py](apps/backend/app/main.py).

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

### 3. **Cliente de API Mal Usado**

**Problema**: [apps/frontend/app/page.tsx](apps/frontend/app/page.tsx) usaba `@ts-ignore` y llamaba `.json()` incorrectamente.  
**Solución**: El cliente generado por Orval ya retorna `{ status, data }`, no necesita `.json()`.

**Antes**:

```tsx
const res = await ask({ query: text, top_k: 3 });
const data = await res.json(); // ❌ Error
```

**Después**:

```tsx
const res = await askV1AskPost({ query: text, top_k: 3 });
setAnswer(res.data.answer); // ✅ Correcto
```

---

### 4. **Configuración de Next.js Duplicada**

**Problema**: Existían `next.config.ts` y `next.config.mjs` simultáneamente.  
**Solución**: Consolidada la configuración de rewrites (proxy al backend) en [next.config.ts](apps/frontend/next.config.ts).

**Nota**: `next.config.mjs` puede eliminarse manualmente si sigue presente.

---

### 5. **Falta de Índice Vectorial**

**Problema**: La tabla `chunks` no tenía índice para búsquedas vectoriales, resultando en queries lentas.  
**Solución**: Agregado índice IVFFlat en [infra/postgres/init.sql](infra/postgres/init.sql).

```sql
CREATE INDEX IF NOT EXISTS chunks_embedding_idx
  ON chunks USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);
```

---

## 🚀 Cómo Ejecutar el Proyecto

### 1. Configurar la API Key

```bash
cp .env.example .env
# Edita .env y agrega tu GOOGLE_API_KEY
```

### 2. Levantar la Infraestructura

```bash
pnpm docker:up
```

### 3. Instalar Dependencias

```bash
pnpm install
```

### 4. Generar Contratos

```bash
pnpm contracts:export
pnpm contracts:gen
```

### 5. Ejecutar en Desarrollo

```bash
pnpm dev
```

- **Frontend**: http://localhost:3000
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs

---

## 📝 Notas Adicionales

### Para Producción

- Cambiar `allow_origins` en CORS a dominio específico
- Agregar autenticación/autorización
- Implementar rate limiting
- Agregar logging estructurado
- Configurar health checks completos

### Base de Datos

Si ya tenías una DB corriendo, necesitás recrearla para aplicar el índice:

```bash
pnpm docker:down
pnpm docker:up
```

### Desarrollo Local Sin Docker

Si querés correr Postgres localmente:

```bash
# Ejecuta el init.sql manualmente
psql -U postgres -d rag -f infra/postgres/init.sql
```
