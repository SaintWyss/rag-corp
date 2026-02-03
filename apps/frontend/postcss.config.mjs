/**
===============================================================================
TARJETA CRC — apps/frontend/postcss.config.mjs (PostCSS Pipeline)
===============================================================================

Responsabilidades:
  - Definir plugins de PostCSS usados por el frontend.
  - Integrar Tailwind CSS en el pipeline de build.

Colaboradores:
  - PostCSS
  - Tailwind CSS
===============================================================================
*/

const config = {
  plugins: {
    "@tailwindcss/postcss": {},
  },
};

export default config;
