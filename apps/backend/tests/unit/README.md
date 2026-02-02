# Test: Unit Tests

## 🎯 Misión

Verificar la lógica de negocio y comportamiento de componentes en aislamiento.
Son la base de la pirámide: rápidos, deterministas y abundantes.

**Qué SÍ hace:**

- Testea Use Cases mockeando repositorios.
- Testea Entidades y Value Objects puros.
- Testea Parsers con inputs fijos.

**Qué NO hace:**

- No toca la Base de Datos real.
- No hace peticiones HTTP reales.

## 🗺️ Mapa del territorio

| Recurso           | Tipo       | Responsabilidad (en humano)                                                |
| :---------------- | :--------- | :------------------------------------------------------------------------- |
| `api/`            | 📁 Carpeta | Tests de controladores y lógica HTTP (aislados).                           |
| `application/`    | 📁 Carpeta | Tests de Casos de Uso (Core Logic).                                        |
| `domain/`         | 📁 Carpeta | Tests de Entidades (raro, pero posible si hay lógica compleja).            |
| `infrastructure/` | 📁 Carpeta | Tests de adaptadores usando mocks (ej. testear el parser con un PDF fake). |

## ⚙️ ¿Cómo funciona por dentro?

Usa `unittest.mock` o implementaciones `InMemory` de los puertos.
Ejecución: milisegundos por test.

## 👩‍💻 Guía de uso (Snippets)

### Estructura típica

```python
def test_create_user_success():
    repo = InMemoryUserRepository()
    use_case = CreateUserUseCase(repo)
    user = use_case.execute(...)
    assert user.id is not None
```

## 🔎 Ver también

- [Tests Hub](../README.md)
