# Despliegue — canchaya. FASE 1

## Componentes

| Pieza | Artefacto | Notas |
|---|---|---|
| Backend | `backend/Dockerfile` (Python 3.12 + gunicorn) | migra al arrancar salvo `DESPLIEGUE_SIN_MIGRATE=1` |
| Frontend | `frontend/Dockerfile` (Vite build + nginx) | proxy `/api/` → `backend:8000`, sin CORS |
| BD | Supabase Postgres (externa) | el `DATABASE_URL` usa el Session pooler |
| Auth | Supabase Auth | el backend solo valida JWT |

## Local con Docker

```powershell
cd canchaya
# 1. Variables que necesita docker-compose.prod.yml
$env:VITE_SUPABASE_URL="https://<ref>.supabase.co"
$env:VITE_SUPABASE_ANON_KEY="<anon key>"

# 2. Levantar
docker compose -f docker-compose.prod.yml up --build
```

- App: **http://localhost:8080** (nginx → SPA + `/api/` proxya al backend).
- Backend directo: **http://localhost:8000/api/v1/health/**.
- Con Supabase remoto, `POSTGRES_HOST` del compose se ignora porque `DATABASE_URL`
  tiene prioridad (ver `config/settings/base.py`).

> ⚠️ El compose define un servicio `db` **solo** para despliegues sin Supabase.
> Si usas el proyecto de Supabase, puedes borrarlo y quitar el `depends_on`.

## Sin Docker (solo producción del frontend)

```powershell
cd frontend
$env:VITE_SUPABASE_URL="https://<ref>.supabase.co"
$env:VITE_SUPABASE_ANON_KEY="<anon key>"
cmd /c "npm ci"
cmd /c "npm run build"        # genera dist/
```

Sube `dist/` a cualquier host estático y configura la API en el mismo origen
(proxy `/api` → backend) para evitar CORS.

## Variables de producción (backend)

```dotenv
DJANGO_SETTINGS_MODULE=config.settings.prod
DJANGO_SECRET_KEY=<64+ caracteres aleatorios>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=api.cancha.com,localhost
DATABASE_URL=postgresql://postgres.<ref>:<pw>@aws-1-us-west-2.pooler.supabase.com:5432/postgres
SUPABASE_URL=https://<ref>.supabase.co
SUPABASE_JWT_SECRET=<legacy secret HS256>   # dejar vacío si el proyecto usa RS256 (JWKS)
CORS_ALLOWED_ORIGINS=https://panel.cancha.com
CSRF_TRUSTED_ORIGINS=https://panel.cancha.com
GUNICORN_WORKERS=3
```

`config/settings/prod.py` ya activa: `SECURE_SSL_REDIRECT`, HSTS 30 días,
cookies `Secure`, `X-Frame-Options: DENY`, `nosniff` y `Referrer-Policy`.

## Healthcheck

```powershell
curl https://api.cancha.com/api/v1/health/
# {"status":"ok","database":true}
```

Es el mismo endpoint que usa el `HEALTHCHECK` del contenedor. Devuelve
`database:false` si el pooler no responde, sin exponer el error.

## Checklist previo a producir

- [ ] `DJANGO_DEBUG=False` y `SECRET_KEY` distinta a la de desarrollo
- [ ] `ALLOWED_HOSTS` y `CORS_ALLOWED_ORIGINS` solo con dominios reales
- [ ] `migrate` ejecutado (o `DESPLIEGUE_SIN_MIGRATE=1` con migración aparte)
- [ ] `manage.py check --deploy` sin `WARNING` críticos
- [ ] Contraseña de `DATABASE_URL` sin corchetes `[...]`
- [ ] Anon key **solo** en el frontend; la `service_role` en ningún sitio
- [ ] Backup de la BD verificado
