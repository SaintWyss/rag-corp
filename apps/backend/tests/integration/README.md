# Test: Integration Tests

## 🎯 Misión

Verificar que los componentes "hablan" bien entre sí y con la infraestructura real.
El foco principal es la **Base de Datos** y las **Queries**.

**Qué SÍ hace:**

- Conecta a una Postgres real.
- Verifica que el SQL manual funciona y retorna lo esperado.
- Verifica constraints (Foreign Keys, Uniques).

**Qué NO hace:**

- No llama a APIs externas reales (Google, AWS) - esas se mockean para evitar costos y flakiness.

## 🗺️ Mapa del territorio

| Recurso           | Tipo       | Responsabilidad (en humano)                                      |
| :---------------- | :--------- | :--------------------------------------------------------------- |
| `infrastructure/` | 📁 Carpeta | Tests de repositorios Postgres.                                  |
| `api/`            | 📁 Carpeta | Tests de endpoints HTTP golpeando la DB real (Functional Tests). |

## ⚙️ ¿Cómo funciona por dentro?

El `conftest.py` (nivel padre) configura una sesión de DB transaccional o trunca tablas.
Requiere que `docker-compose up db` esté corriendo o que el runner de CI levante un servicio postgres.

## 👩‍💻 Guía de uso (Snippets)

### Test de Repositorio Real

```python
@pytest.mark.asyncio
async def test_save_document_pg(pg_repo):
    await pg_repo.save(doc)
    fetched = await pg_repo.get(doc.id)
    assert fetched.title == doc.title
```

## 🔎 Ver también

- [Tests Hub](../README.md)
