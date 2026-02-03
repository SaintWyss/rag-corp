# apps/frontend/app

Este directorio implementa el **App Router** de Next.js, definiendo la estructura de URLs y layouts de la aplicación.

## 🗺️ Mapa de Rutas

Aquí se define **"el qué"** (qué URLs existen), mientras que `src/` define **"el cómo"** (la implementación lógica).

| Ruta            | Descripción                                      | Acceso          |
| :-------------- | :----------------------------------------------- | :-------------- |
| `/`             | Landing page (redirect a login o app).           | Público         |
| `/login`        | Pantalla de inicio de sesión.                    | Público (Guest) |
| `/admin/*`      | Portal de administración (Usuarios, Workspaces). | Rol: Admin      |
| `/workspaces/*` | Portal de empleados (Chat, Documentos).          | Rol: Employee   |

## 🏗️ Estructura de Directorios

### Grupos de Rutas (Route Groups)

Usamos paréntesis `( )` para agrupar rutas sin afectar la URL.

- **`(auth)`**: Rutas relacionadas con autenticación (Login). Tienen layouts minimalistas.
- **`(app)`**: Rutas principales de la aplicación. Comparten el layout con navegación, sidebar y providers de sesión.

### Archivos Especiales

- **`layout.tsx`**: Layout raíz. Define `<html>`, `<body>` y fuentes globales (Geist).
- **`loading.tsx`**: UI de carga por defecto (Suspense) para navegaciones lentas.
- **`error.tsx`**: Error boundary global para capturar excepciones no manejadas.
- **`globals.css`**: Estilos base de Tailwind y resets CSS.

---

# =============================================================================

# TARJETA CRC — apps/frontend/app (Router Root)

# =============================================================================

# Responsabilidades:

# - Definir layout raíz (RootLayout).

# - Configurar fuentes y metadatos globales (SEO).

# - Manejar errores globales y estados de carga.

# Colaboradores:

# - Next.js App Router

# - Tailwind CSS (globals.css)

# =============================================================================
