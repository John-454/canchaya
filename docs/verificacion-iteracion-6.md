# Verificación — Iteración 6 (Endurecimiento y entrega)

## 1. Rate limiting (T6.1)

`REST_FRAMEWORK` en `config/settings/base.py`:

```python
"DEFAULT_THROTTLE_CLASSES": [AnonRateThrottle, UserRateThrottle],
"DEFAULT_THROTTLE_RATES": {"anon": "60/min", "user": "300/min", "auth_sync": "20/min"},
```

- `AnonRateThrottle` limita por **IP** las peticiones sin token.
- `UserRateThrottle` limita por usuario autenticado.
- `SyncView` usa `ScopedRateThrottle` con `throttle_scope="auth_sync"`: es el
  endpoint más expuesto (crea perfiles con cualquier token válido).
- Exceso → **429** con el mismo formato `{code, detail}` y cabecera
  `Retry-After` (la pone DRF).

## 2. CORS y CSRF (T6.2)

| Setting | Valor | Efecto |
|---|---|---|
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173` | solo el panel local; configurable por `.env` |
| `CORS_ALLOW_HEADERS` | lista explícita (incluye `authorization`) | no se aceptan cabeceras arbitrarias |
| `CSRF_TRUSTED_ORIGINS` | `http://localhost:5173` | necesario solo si se usan cookies |
| `X_FRAME_OPTIONS` | `DENY` | anti-clickjacking |
| `SECURE_CONTENT_TYPE_NOSNIFF` | `True` | `X-Content-Type-Options: nosniff` |
| `SECURE_REFERRER_POLICY` | `same-origin` | no filtra URLs a terceros |
| `DATA_UPLOAD_MAX_MEMORY_SIZE` | 2 MB | evita subidas gigantes |
| `prod.py` | `SECURE_SSL_REDIRECT`, HSTS 30 d, cookies `Secure`, `SECURE_HSTS_PRELOAD` opcional | endurecimiento real |

`manage.py check --deploy` con settings de producción:
**`System check identified no issues (0 silenced)`**.

> En desarrollo el frontend usa el **proxy de Vite** (`/api` → `:8000`), así que
> CORS ni interviene. Solo aplica si llamas al 8000 desde otro origen.

## 3. Logging (T6.3)

- `django.request` a nivel `WARNING` → se registran los 4xx/5xx con su traza.
- `modules.bookings` a nivel `INFO` para seguir cambios de estado.
- Los errores de token **no** loguean el token (solo el código de error).

## 4. Documentación de API (T6.5)

`shared/openapi.py` define el contrato **OpenAPI 3.1** completo y se sirve en:

```
GET /api/v1/schema/
```

- 19 rutas, 11 esquemas (`Usuario`, `Cancha`, `Imagen`, `Horario`, `Tarifa`,
  `BloquePrecio`, `Reserva`, `PaginaReservas`, `Dashboard`, `ResumenFinanciero`, `Error`).
- Todas las rutas `/admin/*` declaran `security: [{bearerAuth: []}]`.
- Se documentan los códigos 400/401/403/404/409/429 con el esquema `Error`.
- Importable en Postman/Insomnia como colección.

Documentos humanos complementarios:
- `docs/verificacion-iteracion-{1..6}.md` — criterios por fase.
- `docs/entorno-local-login.md` — cómo probar el login real.
- `docs/despliegue.md` — Docker, nginx, variables y checklist.

## 5. Preparación de despliegue (T6.6)

| Artefacto | Contenido |
|---|---|
| `backend/Dockerfile` | Python 3.12-slim, usuario no root, `migrate` al arrancar, gunicorn con 3 workers, `HEALTHCHECK` |
| `backend/.dockerignore` | excluye `.env`, `.venv`, tests, caches |
| `frontend/Dockerfile` | build multi-stage Vite (`VITE_*` como build-args) + nginx |
| `frontend/nginx.conf` | SPA fallback, caché inmutable de `/assets/`, proxy `/api/`, cabeceras de seguridad |
| `docker-compose.prod.yml` | db + backend + frontend, healthchecks y `depends_on` condicional |

## 6. Pruebas añadidas

`shared/tests/test_hardening.py`

| Grupo | Casos |
|---|---|
| **Throttle** | `/auth/sync/` corta en 20/min (429 al 4.º con cupo 3) · anónimo limitado en rutas protegidas · el 429 mantiene el formato `{code}` |
| **Esquema** | `/api/v1/schema/` responde 200 · OpenAPI 3.1 · cubre las 10 rutas obligatorias de la spec · todas las `/admin/*` declaran bearer · **no expone secretos** |
| **CORS** | origen permitido recibe `Access-Control-Allow-Origin` · origen ajeno **no** recibe la cabecera |
| **Cabeceras** | `X-Frame-Options: DENY`, `nosniff` |
| **Contrato de errores** | 401 con reto · 403 `rol_requerido` · 404 `no_encontrado` |

## Criterios de aceptación de la Iteración 6

- [x] Throttle en `/auth/sync/` y por IP/usuario en toda la API
- [x] CORS restringido a orígenes configurados y cabeceras explícitas
- [x] `check --deploy` sin warnings con settings de producción
- [x] Cabeceras de seguridad (`X-Frame-Options`, `nosniff`, `Referrer-Policy`)
- [x] Contrato OpenAPI 3.1 servido y verificado por tests
- [x] Dockerfiles + compose + nginx para backend y frontend
- [x] Healthcheck y checklist de despliegue documentados
- [x] Suite completa en verde
