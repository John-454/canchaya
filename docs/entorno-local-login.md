# Entorno local — login real contra Supabase

Checklist para levantar backend + frontend y validar el flujo de autenticación
antes de la Iteración 6.

---

## 1. Variables de entorno

### `frontend/.env` (crear manualmente)

```dotenv
VITE_SUPABASE_URL=https://<ref>.supabase.co
VITE_SUPABASE_ANON_KEY=<anon key del proyecto>
VITE_API_BASE=/api/v1
```

| Variable | ¿Obligatoria? | Notas |
|---|---|---|
| `VITE_SUPABASE_URL` | ✅ | `https://<ref>.supabase.co` (Project URL del dashboard) |
| `VITE_SUPABASE_ANON_KEY` | ✅ | *Project Settings → API → anon / publishable key*. Es pública por diseño; **nunca** la `service_role` |
| `VITE_API_BASE` | ➖ | Ya tiene default `/api/v1` en `lib/api.ts`; el proxy de Vite la resuelve |

**No hace falta nada más.** El cliente no conoce el JWT secret, ni la BD, ni el
backend. `import.meta.env.VITE_*` se inyectan en tiempo de build (hay que reiniciar
`npm run dev` tras editar el archivo).

### `backend/.env` (ya existe)

Estado verificado:

```dotenv
DATABASE_URL="postgresql://postgres.<ref>:…@aws-1-us-west-2.pooler.supabase.com:5432/postgres?pgbouncer=true"
SUPABASE_URL=https://<ref>.supabase.co
SUPABASE_JWT_SECRET=<definido>          # el proyecto emite HS256
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
```

Diagnóstico: [scripts/check_env_local.py](../backend/scripts/check_env_local.py)
→ `btree_gist 1.7` ✅, usuario `propietario@canchaya.test` con rol
`administrador` ✅, cancha **Cancha La Jugada** ✅.

> ⚠️ La contraseña de `DATABASE_URL` quedó con **corchetes** (`[kOfi…]`). Hoy
> funciona (el driver los tolera), pero conviene quitarlos para evitar sorpresas
> con otras herramientas (psql, DBeaver, CI).

### CORS / orígenes permitidos

`config/settings/base.py`:

```python
CORS_ALLOWED_ORIGINS = config("CORS_ALLOWED_ORIGINS", default="http://localhost:5173", cast=Csv())
CORS_ALLOW_CREDENTIALS = True
```

- **Default ya correcto** para `http://localhost:5173`; no hay `.env` con
  `CORS_ALLOWED_ORIGINS`, así que aplica el default.
- Además, `vite.config.ts` tiene **proxy** `/api → http://127.0.0.1:8000`, de modo
  que en desarrollo las peticiones salen del mismo origen (`:5173`) y **CORS no
  se usa salvo que llames al 8000 directamente**.
- `django-cors-headers` está en `MIDDLEWARE` antes de `CommonMiddleware` ✅.

Si algún día sirves el build estático desde otro puerto (p. ej. `vite preview` en
4173), añade:

```dotenv
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173
```

---

## 2. Pasos exactos

### A. Backend

```powershell
cd backend
$env:PYTHONPATH = (Get-Location).Path
.\.venv\Scripts\python.exe scripts\check_env_local.py     # diagnóstico
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

### B. Frontend

```powershell
cd frontend
# 1. crear .env con las 2 variables (ver arriba)
cmd /c "npm run dev"        # http://localhost:5173
```

### C. Verificar el administrador

```powershell
cd backend
# ¿Existe el usuario de Supabase Auth con ese correo?
.\.venv\Scripts\python.exe manage.py shell -c "from modules.users_auth.models import Usuario; u=Usuario.objects.get(correo='propietario@canchaya.test'); print(u.rol, u.activo, u.supabase_uid)"
```

Tres escenarios:

| Situación | Acción |
|---|---|
| No existe en **Supabase Auth** | *Authentication → Users → Add user* con `propietario@canchaya.test` y contraseña; copiar el **User UID** |
| Existe en Auth pero con **otro UID** que la BD | `manage.py aprovisionar_admin --correo propietario@canchaya.test --uid <UID>` |
| No tiene cancha | `aprovisionar_admin ... --cancha "Cancha La Jugada" --direccion "..."` |

> El seed usa un UID ficticio (`00000000-0000-4000-8000-000000000001`). En el
> primer login real, `resolver_usuario_autenticado()` **vincula por correo** y
> reemplaza ese UID por el verdadero, conservando el rol. Es el comportamiento
> esperado de la Opción A.

### D. Flujo en el navegador

1. `http://localhost:5173` → redirige a `/login` (guard `RequireAuth`).
2. Email + contraseña → `supabase.auth.signInWithPassword`.
3. `AuthProvider` recibe la sesión → `POST /api/v1/auth/sync/`.
4. Respuesta con `rol: "administrador"` → `RequireRol` deja pasar a `/panel`.
5. Recarga con F5 → la sesión persiste (localStorage) y no vuelve a pedir login.
6. Botón **Salir** → `supabase.auth.signOut()` → vuelve a `/login`.

### E. Prueba automatizada del backend (sin navegador)

```powershell
# con runserver activo
cd backend
$env:PYTHONPATH = (Get-Location).Path
.\.venv\Scripts\python.exe scripts\smoke_auth.py
```

Recorre: sin token → 401 · firma inválida → 401 · expirado → 401 · perfil
inexistente → 401 · sync de cliente → 200 `rol=cliente` · cliente en panel →
403 `rol_requerido` · escalada de rol → 400 `campo_no_permitido` · admin → 200
en `/admin/field/`, dashboard y preview.

---

## 3. Qué observar (red y logs)

### Pestaña *Network* del navegador (filtro `api/`)

| Petición | Esperado | Significado |
|---|---|---|
| `POST https://<ref>.supabase.co/auth/v1/token?grant_type=password` | **200** | credenciales válidas |
| `POST /api/v1/auth/sync/` | **200** `{rol: "administrador", requiere_telefono: false, creado: false}` | perfil vinculado |
| `GET /api/v1/admin/finance/dashboard/` | **200** | guard OK, datos reales |
| `GET /api/v1/admin/field/` | **200** | cancha 1:1 resuelta |
| `POST /auth/sync/` con contraseña mala | **401** `code: invalid_credentials` (lo devuelve **Supabase**, no Django) | el frontend muestra "Correo o contraseña incorrectos" |
| `GET /admin/field/` sin token | **401** + `WWW-Authenticate: Bearer realm="api"` | guard de sesión |
| `GET /admin/field/` con token de **cliente** | **403** `{code: "rol_requerido"}` | `RequireRol` + `IsFieldAdmin` |
| `GET /admin/field/` con admin **sin cancha** | **403** `{code: "admin_sin_cancha"}` | falta aprovisionar cancha |
| `POST /admin/bookings/{id}/approve/` sobre una ya confirmada | **409** `{code: "estado_invalido"}` | máquina de estados |
| `POST /admin/field/schedules/` con solape | **409** `{code: "horario_solapado"}` | R2 |
| `PATCH /auth/me/` con `{rol: ...}` | **400** `{code: "campo_no_permitido"}` | no se puede escalar rol |

### Consola del navegador

- Debe aparecer **cero** errores de CORS y **cero** 401 en bucle (el cliente
  reintenta una sola vez).
- Advertencia esperada de React Router sobre *future flags* (inofensiva).

### Logs del backend (terminal de `runserver`)

```
"POST /api/v1/auth/sync/ HTTP/1.1" 200
"GET /api/v1/admin/field/ HTTP/1.1" 200
WARNING Forbidden: /api/v1/admin/field/          <- esperado con token de cliente (403)
Not Found: /api/v1/admin/bookings/999/           <- esperado si pruebas un id ajeno
```

### Checklist de aceptación

- [ ] `/login` sin sesión; `/panel` sin sesión redirige a `/login`
- [ ] Login correcto → `sync 200` con `rol=administrador` → entra al Dashboard
- [ ] Login con contraseña mala → mensaje "Correo o contraseña incorrectos" (sin llamar al backend)
- [ ] F5 mantiene la sesión; "Salir" la revoca
- [ ] Con una cuenta de **cliente** → pantalla "Acceso restringido"
- [ ] Los KPIs del Dashboard coinciden con `GET /admin/finance/dashboard/`
