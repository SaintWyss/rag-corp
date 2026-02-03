# apps/frontend/app/(auth)

Grupo de rutas dedicado a la **Autenticación**.

## 🎯 Propósito

Agrupar pantallas que:

1. Son públicas (o para usuarios no logueados).
2. Requieren un layout diferente al de la app principal (sin sidebar, sin header de navegación, centrado en el contenido).

## 📍 Rutas

| Ruta     | Archivo          | Descripción                                                 |
| :------- | :--------------- | :---------------------------------------------------------- |
| `/login` | `login/page.tsx` | Formulario de inicio de sesión. Maneja redirect post-login. |

---

# =============================================================================

# TARJETA CRC — apps/frontend/app/(auth) (Auth Group)

# =============================================================================

# Responsabilidades:

# - Proveer un contexto visual limpio para login/registro.

# - Aislar el layout de autenticación del layout de la aplicación principal.

# Colaboradores:

# - `src/features/auth` (Lógica de login)

# - `middleware.ts` (Redirección hacia/desde aquí)

# =============================================================================
