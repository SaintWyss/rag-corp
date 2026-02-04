<!--
===============================================================================
TARJETA CRC - deploy/README.md
===============================================================================
Responsabilidades:
- Documentar el template GitOps para multiples instancias (tenants/envs).
- Definir convenciones de naming, promocion y rollback.

Colaboradores:
- deploy/tenants/*/*/values.yaml
- deploy/argocd/applicationset.yaml
- infra/helm/ragcorp (chart)

Invariantes:
- No incluir secretos en git.
- Usar el chart infra/helm/ragcorp sin modificar APIs.
===============================================================================
-->
# GitOps Template — RAG Corp (multi-instancia)

Este directorio es un **template GitOps** pensado para moverse a un repo de despliegue dedicado. Soporta multiples instancias (tenants) con staging/prod sin convertir la app en multi-tenant.

## Convenciones

- **Namespace:** `ragcorp-<tenant>-<env>`
- **Release (Helm):** `ragcorp`
- **Ingress host:** `<tenant>.<env>.example.com` (placeholder)
- **Chart:** `infra/helm/ragcorp`

## Estructura

```
deploy/
├── README.md
├── argocd/
│   └── applicationset.yaml
└── tenants/
    ├── company-a/
    │   ├── staging/values.yaml
    │   └── prod/values.yaml
    └── company-b/
        ├── staging/values.yaml
        └── prod/values.yaml
```

## Promocion (staging → prod)

1) Abrir PR que actualice el **tag/digest de imagen** en `deploy/tenants/<tenant>/prod/values.yaml`.
2) Merge al main del repo de deploy.
3) GitOps sincroniza prod automaticamente.

## Rollback

Opcion A (GitOps): revertir el commit que cambio el tag/digest.

Opcion B (Helm):
```bash
helm rollback ragcorp <REVISION> -n ragcorp-<tenant>-<env>
```

## Secretos

No se versionan secretos. Usar `secrets.existingSecret` o un ExternalSecrets (recomendado).

## Validacion local

```bash
helm template ragcorp infra/helm/ragcorp -f deploy/tenants/company-a/staging/values.yaml > /tmp/ragcorp-company-a-staging.yaml
```

## Nota sobre vendor-neutralidad

El template incluye un `ApplicationSet` de Argo CD como **ejemplo**. Puede adaptarse facilmente a Flux (Kustomization) sin cambios en los valores.
