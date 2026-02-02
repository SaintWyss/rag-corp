# Layer: Worker (Async Processing)

## 🎯 Misión

Esta carpeta contiene el punto de entrada para los procesos en segundo plano (Workers).
Se encarga de ejecutar tareas pesadas o de larga duración (como procesar PDFs, generar embeddings masivos) fuera del ciclo de petición-respuesta HTTP para no bloquear la API.

**Qué SÍ hace:**

- Inicializa un proceso worker de RQ (Redis Queue).
- Escucha colas específicas (`default`, `high`, `low`).
- Expone un servidor HTTP mínimo (`worker_server.py`) para health checks (Kubernetes probes).

**Qué NO hace:**

- No define la lógica de los jobs (eso está en `application` o `infrastructure/queue`).
- No maneja peticiones de usuarios finales.

**Analogía:**
Si la API es la persona que toma el pedido en el mostrador, el Worker es el cocinero en el fondo preparando el plato complejo que tarda 20 minutos.

## 🗺️ Mapa del territorio

| Recurso            | Tipo       | Responsabilidad (en humano)                                      |
| :----------------- | :--------- | :--------------------------------------------------------------- |
| `jobs.py`          | 🐍 Archivo | Definiciones de los jobs que RQ puede ejecutar.                  |
| `worker.py`        | 🐍 Archivo | **Entrypoint**. Script que arranca el proceso worker.            |
| `worker_health.py` | 🐍 Archivo | Lógica para chequear si el worker está "sano".                   |
| `worker_server.py` | 🐍 Archivo | Servidor HTTP simple para exponer `/healthz` en puerto separado. |

## ⚙️ ¿Cómo funciona por dentro?

### Tecnologías

- **RQ (Redis Queue):** Sistema de colas simple basado en Redis.
- **Redis:** Broker de mensajes.

### Flujo

1.  Se ejecuta `python -m app.worker.worker`.
2.  El script conecta a Redis e instancia un `Worker`.
3.  Arranca un thread separado con `worker_server` para responder a health checks (puerto 8001 por defecto).
4.  El worker entra en loop infinito haciendo "polling" a Redis buscando tareas.
5.  Cuando encuentra una tarea, hace fork (o usa el mismo proceso) y ejecuta la función Python correspondiente.

## 🔗 Conexiones y roles

- **Rol Arquitectónico:** Entry Point (Async).
- **Recibe órdenes de:** La infraestructura de despliegue (Docker/K8s).
- **Consume:** Tareas encoladas por la capa de `application`.
- **Llama a:** `app.infrastructure.db` (para conectar a DB durante el job).

## 👩‍💻 Guía de uso (Snippets)

### Arrancar el Worker manualmente

```bash
# Desde apps/backend/
# Asegúrate de que Redis esté corriendo
export REDIS_URL=redis://localhost:6379/0
python -m app.worker.worker
```

### Encolar un trabajo (desde la app)

(Esto normalmente lo hace `infrastructure/queue`, pero conceptualmente:)

```python
from app.infrastructure.queue.rq_queue import queue
# queue.enqueue(...)
```

## 🧩 Cómo extender sin romper nada

1.  **Nuevas Colas:** Si defines una nueva cola en `config`, asegúrate de que el worker la escuche (argumentos en `worker.py`).
2.  **Timeout:** Ajusta el timeout de los jobs si tus tareas de PDF son muy largas.

## 🆘 Troubleshooting

- **Síntoma:** El worker arranca pero no procesa nada.
  - **Causa:** Puede estar escuchando la cola incorrecta o Redis está vacío.
- **Síntoma:** `WorkHorse terminated unexpectedly`.
  - **Causa:** El job consumió demasiada memoria (OOM) o segfault en librerías C.

## 🔎 Ver también

- [Infraestructura de Cola (RQ Wrapper)](../infrastructure/queue/README.md)
