# ADR-001: Adopción de Clean Architecture

## Estado

**Aceptado** (2024-12)

## Contexto

El sistema RAG Corp necesita:
- Lógica de negocio testeable sin dependencias de infraestructura
- Flexibilidad para cambiar proveedores (LLM, DB) sin refactors masivos
- Separación clara de responsabilidades para equipos distribuidos

## Decisión

Adoptamos **Clean Architecture** con cuatro capas:

1. **Domain**: Entidades y Protocols (contratos)
2. **Application**: Use cases (lógica de negocio)
3. **Infrastructure**: Implementaciones (DB, APIs externas)
4. **API**: HTTP layer (FastAPI)

### Reglas de dependencia

```
API → Application → Domain ← Infrastructure
```

- Domain no importa nada externo
- Application solo importa Domain
- Infrastructure implementa Protocols de Domain
- API orquesta con Dependency Injection

## Consecuencias

### Positivas

- **Testabilidad**: Use cases se testean con mocks/fakes sin DB real
- **Flexibilidad**: Cambiar de Google a OpenAI = nueva clase en Infrastructure
- **Claridad**: Cada capa tiene responsabilidad única

### Negativas

- **Boilerplate**: Más archivos y clases que arquitectura flat
- **Curva de aprendizaje**: Requiere entender Protocols y DI

## Alternativas consideradas

1. **Arquitectura flat** (todo en routes.py) - Descartada por acoplamiento
2. **Hexagonal** - Similar, preferimos terminología Clean Architecture
3. **CQRS** - Overhead innecesario para volumen actual

## Referencias

- [Clean Architecture - Robert C. Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [backend/app/domain/](../../../backend/app/domain/)
- [backend/app/application/](../../../backend/app/application/)
