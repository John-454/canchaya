# Verificación — Iteración 5 (Panel React del administrador)

## 1. Estructura de carpetas y plan de vistas

```text
frontend/
├── index.html
├── package.json               # React 18, React Query 5, Supabase JS, Vite 5, Vitest
├── vite.config.ts             # proxy /api -> 127.0.0.1:8000 (evita CORS en dev)
├── tailwind.config.ts         # tokens de Canva (dark #0a2328, action #15803d)
├── .env.example               # VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY
└── src/
    ├── main.tsx
    ├── App.tsx                # QueryClient + Router + AuthProvider + guardas
    ├── index.css              # Tailwind + focus visible
    ├── api/
    │   ├── types.ts           # tipos espejo de los serializers (§5)
    │   ├── endpoints.ts       # authApi, canchaApi, imagenesApi, horariosApi,
    │   │                      #   tarifasApi, reservasApi, finanzasApi
    │   └── queryKeys.ts       # claves de caché + KEYS_AFECTADAS_POR_RESERVA
    ├── lib/
    │   ├── api.ts             # fetch tipado, ApiError, Bearer + reintento 401
    │   ├── supabase.ts        # cliente Auth, login email/Google, refresh
    │   └── format.ts          # COP, fechas es-CO, HH:MM, lunesDe/sumarDias
    ├── auth/
    │   ├── AuthProvider.tsx   # sesión Supabase -> /auth/sync/ -> perfil+rol
    │   └── guards.tsx         # RequireAuth / RequireRol
    ├── components/
    │   ├── AppShell.tsx       # sidebar oscura + header
    │   ├── ui.tsx             # Card, Badge, Boton, Campo, clasesInput
    │   ├── estados.tsx        # Cargando, Vacio, ErrorApi (por status)
    │   ├── BarChart.tsx       # gráfico sin dependencias, accesible
    │   └── SinPermiso.tsx     # 403 por rol
    ├── pages/
    │   ├── LoginPage.tsx          # email/contraseña + Google
    │   ├── DashboardPage.tsx      # 6 KPIs, 2 series, solicitudes, próximos
    │   ├── MiCanchaPage.tsx       # formulario + estado publicado
    │   ├── FotografiasPage.tsx    # alta por URL, principal, borrar
    │   ├── HorariosPage.tsx       # L-D con varias franjas, 409 visible
    │   ├── TarifasPage.tsx        # semanales, especiales, vista previa
    │   ├── ReservasPage.tsx       # tabla + filtros + drawer + acciones
    │   ├── CalendarioPage.tsx     # semana, 7 consultas en paralelo
    │   └── ContabilidadPage.tsx   # periodos + historial
    └── test/                  # Vitest + Testing Library
```

### Dependencias elegidas y por qué

| Paquete | Motivo |
|---|---|
| `@tanstack/react-query` | caché por clave, invalidación selectiva, `isLoading/isError/isPending` listos |
| `@supabase/supabase-js` | sesión, refresh de token y Google OAuth sin backend intermedio |
| `react-router-dom` | rutas anidadas bajo `/panel` con `Outlet` |
| `tailwindcss` | tokens exactos del diseño de Canva en `tailwind.config.ts` |
| `vitest` + `@testing-library/react` + `jsdom` | tests de componentes sin navegador |

### Comandos (Windows/PowerShell)

`npm.ps1` está bloqueado por la Execution Policy, así que se usa `npm.cmd`:
en esta máquina el runner es `cmd /c "npm ..."`.

```powershell
cd frontend
cmd /c "npm install"
cmd /c "npm run dev"          # http://localhost:5173
cmd /c "npm run test"         # vitest run
cmd /c "npm run build"        # tsc -b && vite build
```

---

## 2. Sesión, errores y consumo de la API

### Autenticación (Supabase)

```text
LoginPage --(email/pass | Google)--> supabase.auth
        --> AuthProvider escucha onAuthStateChange
        --> POST /api/v1/auth/sync/  (rol + requiere_telefono)
        --> RequireRol('administrador') habilita /panel/*
```

- La sesión persiste en `localStorage` (`persistSession`, `autoRefreshToken`).
- `setTokenProvider()` registra la función que entrega el token al cliente HTTP;
  `getAccessToken()` refresca si faltan <30 s para expirar.
- El backend **nunca** se llama sin token: `Base = /api/v1`, la cabecera
  `Authorization: Bearer <jwt>` se añade en cada petición.
- Si `/auth/sync/` falla, el `AuthProvider` pasa a `estado='error'` con el
  mensaje real del backend (p. ej. `cuenta_desactivada`).

### Guardas

| Estado | Resultado |
|---|---|
| `cargando` | `<Cargando mensaje="Verificando permisos…" />` |
| `anonimo` | `Navigate /login` (conservando `from`) |
| `rol !== administrador` | `<SinPermiso />`: "Esta sección requiere el rol administrador" + cerrar sesión |
| `admin_sin_cancha` (403 del backend) | `ErrorApi` con el mensaje de negocio y el código |

### Mapa de errores → UI

`ApiError` normaliza **todo** a `{ status, code, detail, errors }` y expone
`mensajeUsuario`:

| HTTP | Ejemplo de `code` | Qué ve el usuario |
|---|---|---|
| **400** | `bloque_no_alineado`, `fuera_de_horario`, `telefono_invalido`, `parametros_invalidos` | "Las horas deben estar en punto…", "El rango incluye un bloque fuera del horario…" |
| **401** | `token_expirado`, `token_invalido`, `perfil_no_sincronizado` | "Tu sesión expiró…" + **se reintenta una vez** (el provider refresca) y queda el botón *Reintentar* |
| **403** | `rol_requerido`, `admin_sin_cancha`, `cuenta_desactivada` | "Esta sección es exclusiva para administradores" / "no tiene una cancha asignada" |
| **409** | `horario_solapado`, `tarifa_solapada`, `estado_invalido`, `horario_no_disponible`, `reserva_ya_pagada` | "Esa franja se solapa…", "La reserva cambió de estado; actualiza la lista" |
| **5xx / red** | — | "No pudimos conectar con el servidor" |

Cada `ErrorApi` lleva `data-testid="error-api-<status>"`, lo que permite a los
tests afirmar exactamente qué tipo de error se pintó.

**Reintentos**: React Query no reintenta 4xx (solo `>= 500`, máx. 2 veces),
porque un `409` no va a cambiar por insistir.

**Invalidación tras mutaciones**: aprobar/cancelar/pagar invalida
`dashboard`, `reservas` y `summary` a la vez (`KEYS_AFECTADAS_POR_RESERVA`), de
modo que KPIs, lista y contabilidad quedan coherentes sin recargar la página.

### Endpoints consumidos

| Vista | Endpoints |
|---|---|
| Login/Auth | `POST /auth/sync/`, `GET /auth/me/` |
| Dashboard | `GET /admin/finance/dashboard/` + `POST /admin/bookings/{id}/approve|cancel/` |
| Mi cancha | `GET/PATCH /admin/field/` |
| Fotografías | `GET/POST /admin/field/images/`, `PATCH/DELETE .../images/{id}/` |
| Horarios | `GET/POST /admin/field/schedules/`, `PUT/DELETE .../schedules/{id}/` |
| Tarifas | `GET/POST /admin/field/rates/`, `DELETE .../rates/{id}/`, `GET .../rates/preview/?fecha=` |
| Reservas | `GET /admin/bookings/?fecha&estado_reserva&estado_pago&cliente&codigo_reserva&page` + 3 acciones |
| Calendario | `GET /admin/bookings/?fecha=` (7 en paralelo por semana) |
| Contabilidad | `GET /admin/finance/summary/?period=day|week|month|custom` |

---

## 3. Verificaciones y criterios de aceptación

### Suite del frontend (`npm run test`)

| Archivo | Cubre |
|---|---|
| `api.test.ts` | `mensajeUsuario` por código (403/409/400), conservación de `status/code/errors`, fallback |
| `http.test.ts` | Bearer adjuntado, normalización a `ApiError`, query string con filtros vacíos descartados, **reintento único en 401**, 204 sin cuerpo, 403 de rol |
| `format.test.ts` | `HH:MM`, nombres de días, `lunesDe` (ISO, miércoles/domingo), suma de días con cambio de mes |
| `estados.test.tsx` | `ErrorApi` para 400/403/409/500/red + botón Reintentar; `Vacio` |
| `dashboard.test.tsx` | KPIs y solicitudes, vacíos, **aprobar dispara el POST y recarga**, 403 `admin_sin_cancha`, 401 + reintento, fallo de red |
| `horarios-tarifas.test.tsx` | franjas por día + "Cerrado", **409 `horario_solapado`**, semanales vs especiales, **vista previa con los 3 orígenes** |
| `reservas.test.tsx` | listado, drawer con contacto, **aprobar actualiza el estado**, **409 `estado_invalido`**, vacío, paginación (`page=2`) |
| `contabilidad.test.tsx` | ingresos/pendiente/historial, **400 `parametros_invalidos`** |

Además:

```powershell
cmd /c "npm run build"    # tsc -b (strict) + vite build: falla si hay tipos rotos
```

### Verificación manual contra el backend real

1. `python manage.py runserver` + `npm run dev`.
2. Login con el admin aprovisionado (`aprovisionar_admin`).
3. Dashboard: comparar KPIs con `GET /admin/finance/dashboard/`.
4. Tarifas → *Vista previa*: el bloque debe coincidir con `GET /admin/field/rates/quote/`.
5. Horarios: intentar una franja solapada y ver el mensaje de 409.
6. Reservas: aprobar → el KPI "Por aprobar" baja sin recargar.
7. Cuenta **cliente**: entra a `/panel` y ve la pantalla de acceso restringido.

### Criterios de aceptación de la Iteración 5

- [x] Todas las rutas del panel existen y cargan: Dashboard, Mi cancha, Fotografías,
      Horarios, Tarifas, Reservas, Calendario, Contabilidad
- [x] Sin sesión → redirige a `/login`; con rol `cliente` → pantalla de acceso restringido
- [x] No queda ningún texto "Panel demo" ni ruta falsa (verificado en el bundle)
- [x] Las 8 vistas leen datos reales del backend (cero datos hardcodeados)
- [x] `400/401/403/409` muestran mensajes de negocio distintos y accionables
- [x] Un `401` se reintenta una vez tras refrescar el token
- [x] Las mutaciones de reservas refrescan dashboard, listado y contabilidad
- [x] `npm run test` → **39 tests / 9 archivos en verde**
- [x] `npm run build` → `tsc -b` strict + `vite build` sin errores (485 kB / 137 kB gzip)
- [x] `npm run lint` → ESLint 9 flat config sin errores

### Fallos de test corregidos durante la verificación

| Fallo | Causa | Corrección |
|---|---|---|
| `160.000` no encontrado | `Intl` en es-CO intercala espacio duro: `$ 160.000` | Matcher con regex `/160\.000/` |
| `role="button" name="Agregar"` | El botón no existe mientras `isLoading` muestra `<Cargando>`; además el nombre accesible no hace match exacto | `findByRole(/Agregar/)` |
| El 409 no aparecía en Horarios | El mismo mock devolvía 409 también al **GET** del listado → la página quedaba en estado de error | Mock diferenciado por método (GET 200 / POST 409) |
| `204` rechazado | `new Response('null', {status: 204})` es inválido | Cuerpo `null` cuando el status es 204 |
| "Fecha especial" ambiguo | Coincide la `<option>` del formulario y el origen del bloque | `{ selector: 'p' }` |
| Detalle tras aprobar | El drawer conserva la vista y el texto aparece dos veces | Se afirma el diálogo actualizado |
