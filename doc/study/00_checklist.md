# Checklist antes de empezar

- [ ] Lei `README.md` y `doc/README.md`.
- [ ] Copie `.env.example` a `.env` y complete `GOOGLE_API_KEY`.
- [ ] Revise `DATABASE_URL` y el resto de envs en `.env`.
- [ ] Tengo `node`, `pnpm` y `docker compose` disponibles.
- [ ] Corri `pnpm install` en la raiz.
- [ ] Levante servicios con `pnpm docker:up`.
- [ ] Verifique `curl http://localhost:8000/healthz`.
- [ ] Genere contratos: `pnpm contracts:export` y `pnpm contracts:gen`.
- [ ] Corri `pnpm dev`.
- [ ] Abri `http://localhost:3000` y valide que carga la UI.
