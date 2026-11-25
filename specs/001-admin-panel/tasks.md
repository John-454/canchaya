# Plan de Tareas SDD — canchaya. (FASE 1: Backend + Panel Admin)

> **Fuente:** `especificaci_n_base_y_gu_a_sdd_canchaya.md` (v1)
> **Alcance de esta fase:** Núcleo Backend, Base de Datos y Panel de Administrador (1 cancha por propietario).
> **Fuera de alcance v1:** pasarela de pago online, multi-ciudad, registro público de administradores, reservas como invitado, gastos/utilidad neta.

## Convenciones

- **IDs** (`T1.1`, `T2.3`, …) son estables: úsalos en commits y PRs (`feat(T2.2): permission IsFieldAdmin`).
- **[P]** = puede ejecutarse en paralelo con otras tareas del mismo bloque.
- **DoD (Definition of Done) por tarea:** código + al menos 1 test que la verifique + `ruff`/`black` limpios + migraciones aplicables desde cero.
- **Fronteras del monolito modular:** un módulo solo expone un `services.py` / `selectors.py` y `api/serializers.py` + `api/views.py`. **Prohibido** importar `models` de otro módulo (excepto FKs en migraciones).
- **Ruta raíz:** `C:\Users\JOHN  CHITAN\canchaya` → `backend/`, `frontend/`, `specs/`.

---

## Iteración 0 — Preparación del repositorio

- [ ] **T0.1** Inicializar repo git, `.gitignore` (Python, Node, `.env`, `*.log`, `.venv`), `.editorconfig`.
- [ ] **T0.2** Backend: `uv` o `venv` + `requirements.txt` (`django`, `djangorestframework`, `psycopg[binary]`, `django-cors-headers`, `django-filter`, `python-decouple`, `PyJWT`, `requests`, `pytest`, `pytest-django`, `factory-boy`, `ruff`, `black`).
- [ ] **T0.3** `docker-compose.yml` con PostgreSQL 16 (imagen con `btree_gist` ya incluida en postgres core) + variables de entorno para dev.
- [ ] **T0.4** Estructura de carpetas vacía `backend/config`, `backend/shared`, `backend/modules/*` con `__init__.py` y un `README.md` corto explicando la frontera de cada módulo.
- [ ] **T0.5** `pytest.ini` / `pyproject.toml` con `DJANGO_SETTINGS_MODULE`, `--cov` y `ruff` config.
- [ ] **ADO** (Acceptance Criteria): `docker compose up -d` levanta DB; `pytest` corre con 0 tests y exit 0; `python manage.py check` pasa.

---

## Iteración 1 — Estructura del Monolito Modular y Base de Datos

### 1.1 Configuración Django

- [ ] **T1.1** `config/settings/base.py` con `INSTALLED_APPS` de módulos, `AUTH_USER_MODEL = 'users_auth.Usuario'` (custom user sobre `AbstractBaseUser`/`PermissionsMixin` o tabla propia), DRF defaults (auth por JWT Supabase, `DEFAULT_PAGINATION_CLASS` custom `id`/`page_size` desde `shared/pagination.py`), `TIME_ZONE='America/Bogota'`, `USE_TZ=True`.
- [ ] **T1.2** `config/urls.py` monta `/api/v1/` → `users_auth`, `fields`, `bookings`, `finance` (URLConf por módulo: `modules/x/api/urls.py`).
- [ ] **T1.3** [P] `shared/` helpers: excepciones de dominio (`DomainError`, `ConflictError`, `BusinessRuleViolation`), `shared/dates.py` (`today_in_tz()`, `now_in_tz()`, `week_bounds()`, `month_bounds()`), `shared/pagination.py`, `shared/exceptions_handler.py` (mapea `DomainError` a JSON `{code, detail}`).

### 1.2 Módulo `users_auth` — modelos

- [ ] **T1.4** `modules/users_auth/models.py`: `Usuario` con los campos de §4.1 (`supabase_uid` UUID UNIQUE, `nombre` 120, `correo` `CITEXT` 150 UNIQUE, `telefono` 30 NULL-able a nivel DB, `rol` choices `cliente|administrador`, `activo`, `fecha_creacion`).
  - Constraint: `CheckConstraint(rol IN ('cliente','administrador'))`.
  - Índice en `correo` (o `CITEXT` requiere `CREATE EXTENSION citext` en migración inicial).
  - **R1 (decidido):** `telefono` `null=True` en BD; obligatoriedad se valida en servicio.

### 1.3 Módulo `fields` — modelos

- [ ] **T1.5** `Cancha` (§4.2) con `id_administrador` FK `UNIQUE` → `usuarios` (`limit_choices_to={'rol': 'administrador'}`, `on_delete=PROTECT`).
- [ ] **T1.6** `ImagenCancha` (§4.3) FK `canchas` (`on_delete=CASCADE`); constraint único parcial `imagen_principal IS TRUE` por `id_cancha` → `UniqueConstraint(fields=['id_cancha'], condition=Q(imagen_principal=True), name='uq_imagen_principal_por_cancha')`.
- [ ] **T1.7** `HorarioOperacion` (§4.4): `dia_semana` 1..7 (`CheckConstraint`), `hora_apertura < hora_cierre` (`CheckConstraint` si es semánticamente obligatorio), `activo`.
  - Exclusión GIST: `ExclusionConstraint(name='ex_horario_no_solape', expressions=[('id_cancha','=','id_cancha'), ('dia_semana','=', 'dia_semana'), (RangeAgg/ `TstzRange` sobre `hora_apertura`/`hora_cierre`, '&&')], condition=Q(activo=True))` — verificar API exacta de Django 5.x para ranges de `TimeField` (puede requerir `Func`/`tsrange`). **Riesgo R2.**
- [ ] **T1.8** `Tarifa` (§4.5): `dia_semana` NULL, `fecha_especial` NULL, `hora_inicio < hora_fin`, `precio_hora > 0`.
  - `CheckConstraint`: `(dia_semana IS NOT NULL AND fecha_especial IS NULL) OR (dia_semana IS NULL AND fecha_especial IS NOT NULL)`.
  - Exclusión GIST doble: una para tarifas semanales `(id_cancha, dia_semana, time_range)` con `condition=Q(dia_semana__isnull=False, activo=True)`; otra para especiales `(id_cancha, fecha_especial, time_range)` con `condition=Q(fecha_especial__isnull=False, activo=True)`.

### 1.4 Módulo `bookings` — modelos

- [ ] **T1.9** `Reserva` (§4.6) con todos los campos, `id_cliente` FK `usuarios` `on_delete=RESTRICT`, `nombre_cliente`/`correo_cliente`/`telefono_cliente` **snapshot** denormalizado (se copian al crear).
  - `CheckConstraint` `hora_inicio < hora_fin`; `estado_reserva IN ('Pendiente','Confirmada','Cancelada','Finalizada')`; `estado_pago IN ('Pendiente','Pagado')`.
  - `CheckConstraint`: `(estado_pago='Pagado' AND fecha_pago IS NOT NULL) OR (estado_pago='Pendiente' AND fecha_pago IS NULL)`.
  - `UniqueConstraint(codigo_reserva)`; índice `(id_cancha, fecha_reserva)`; índice `(estado_reserva, fecha_reserva, hora_fin)` para el job de Finalización.
  - Exclusión GIST: `(id_cancha =, fecha_reserva =, time_range &&)` `condition=Q(estado_reserva__in=['Pendiente','Confirmada'])`.
  - Generación de `codigo_reserva` `CY-YYMMDD` + sufijo/aleatorio para evitar colisión → mover a T3.1 (servicio).

### 1.5 Migraciones y verificación

- [ ] **T1.10** Migración `0001` con `RunSQL('CREATE EXTENSION IF NOT EXISTS btree_gist')` y `CREATE EXTENSION IF NOT EXISTS citext` **antes** de crear tablas; `makemigrations` para el resto.
- [ ] **T1.11** [P] Tests de constraints en `modules/<x>/tests/test_constraints.py`:
  - doble `imagen_principal` → `IntegrityError`
  - horarios solapados mismo día → `IntegrityError`; franjas en días distintos / contiguas (`08-12`, `12-14`) → OK
  - tarifa semanal + fecha especial en la misma fila → `IntegrityError`
  - reservas solapadas en estado Pendiente/Confirmada → `IntegrityError`; misma franja con la primera Cancelada → OK
  - `Pagado` sin `fecha_pago` → `IntegrityError`
  - `canchas.id_administrador` duplicado → `IntegrityError`
- [ ] **T1.12** Script `backend/scripts/seed_admin.py` (management command `seed_field_admin`) que crea 1 admin + 1 cancha + horarios 08-12/13-22 L-V + tarifas base demo (idempotente).
- [ ] **ADO:** migraciones aplican desde cero en DB limpia; `pytest modules/*/tests/test_constraints.py` verde; `\d+ reservas` muestra la exclusión parcial.

---

## Iteración 2 — Autenticación Supabase y Permisos por Rol

### 2.1 Validación JWT

- [ ] **T2.1** `shared/auth/supabase.py` → `SupabaseJWTVerifier`:
  - Descarga/cachea JWKS de Supabase (`https://<ref>.supabase.co/auth/v1/.well-known/jwks.json`) y/o valida HS256 con `SUPABASE_JWT_SECRET` (fallback configurable).
  - Valida `exp`, `aud="authenticated"`, `iss`; extrae `sub` (= `supabase_uid`), `email`, `user_metadata`.
  - Falla con `401` tipado (`TokenExpired`, `TokenInvalid`).
- [ ] **T2.2** `shared/auth/authentication.py` → `SupabaseJWTAuthentication(BaseAuthentication)`:
  - Valida token → busca `Usuario` por `supabase_uid` (o `correo` como fallback de vinculación) → setea `request.user`; si no existe, lanza `AuthenticationFailed(code='perfil_no_sincronizado')` para forzar `/auth/sync/`.
  - Respeta `Usuario.activo = False` → `403 cuenta_desactivada`.
  - [P] Tests: token válido, expirado, firma inválida, usuario inactivo, usuario inexistente.

### 2.2 Endpoints de perfil

- [ ] **T2.3** `POST /api/v1/auth/sync/`:
  - Valida token; obtiene o crea `Usuario` (`rol='cliente'` por defecto, `telefono=NULL` si no viene).
  - Actualiza `nombre`/`correo` si cambiaron en Supabase; **nunca** sobrescribe `rol` existente.
  - Retorna perfil + `rol` + `requiere_telefono` (bool = `telefono IS NULL`).
  - Idempotente.
- [ ] **T2.4** `GET /api/v1/auth/me/` (necesario para el frontend y el guard de admin; no está en la spec pero es imprescindible).
- [ ] **T2.5** `PATCH /api/v1/auth/me/`: actualiza `nombre` y/o `telefono` (valida E.164/COL: 10 dígitos móvil, `+57` opcional); ignora intentos de modificar `rol`/`activo` (retorna 400 explícito si se envían).
- [ ] **T2.6** [P] `shared/permissions.py` → `IsFieldAdmin`:
  - `requiere request.user.rol == 'administrador'` y `activo`;
  - expone `request.user.cancha` (lazy, via `fields.services.get_cancha_by_admin(user)`; si no existe → `403 admin_sin_cancha`).
  - `IsCliente` (para fase de cliente reservando; dejar preparado).
- [ ] **T2.7** Servicio `users_auth/services.py`: `sync_usuario()`, `update_perfil()`, `require_telefono(user)` (lanza `BusinessRuleViolation('telefono_requerido')`).
- [ ] **T2.8** Tests de aislamiento: admin A no puede tocar cancha de admin B (se valida sobre endpoints de Iteración 3; aquí se testea el permiso en abstracto con `APIRequestFactory`).
- [ ] **ADO:** `pytest modules/users_auth` verde; `curl` con token real de Supabase crea el usuario cliente; `PATCH /me` con teléfono inválido → 400.

---

## Iteración 3 — Módulo `fields` (Mi Cancha, Fotos, Horarios, Tarifas)

### 3.1 Servicios de dominio

- [ ] **T3.1** `fields/services.py`:
  - `get_mi_cancha(user)`, `update_mi_cancha(user, data)`
  - `list_images/add_image/set_principal/delete_image` (al marcar principal, desmarca el anterior **en la misma transacción**; al borrar la principal, auto-promueve la más antigua restante — decisión documentada).
  - `list_schedules/add_schedule/update_schedule/delete_schedule` (solapamiento se valida en serializer **y** se deja que la constraint DB sea la última barrera; mapear `IntegrityError` → 409 `horario_solapado`).
  - `list_rates/add_rate/update_rate/delete_rate` (mismo patrón → 409 `tarifa_solapada`).
- [ ] **T3.2** `fields/services/pricing.py` → `PricingEngine`:
  - `slots_for_date(cancha, fecha) -> list[Slot(inicio, fin, precio, origen)]` con pasos de 60 min dentro de los `horarios_operacion` activos del `dia_semana` de la fecha.
  - `price_for_range(cancha, fecha, hora_inicio, hora_fin) -> Decimal` sumando precio por bloque.
  - Prioridad: `fecha_especial` > `dia_semana` > `precio_base`; solo tarifas `activo=True` y con `hora_inicio <= bloque < hora_fin`.
  - Función pura (sin requests), testeada exhaustivamente.
- [ ] **T3.3** [P] Tests `PricingEngine`: fecha normal usa precio_base; tarifa semanal pisa base; fecha especial pisa semanal; bloques mixtos (2h con dos tarifas distintas) suman correctamente; fecha sin `horario_operacion` → lista vacía; bloques exactamente en límites (`hora_inicio == tarifa.hora_fin` no aplica).

### 3.2 API

- [ ] **T3.4** `GET/PATCH /api/v1/admin/field/` — serializer valida `precio_base >= 0`, `nombre` requerido, `estado` bool. `PATCH` parcial.
- [ ] **T3.5** `GET/POST /api/v1/admin/field/images/` y `PATCH/DELETE /.../images/{id_imagen}/`:
  - `POST` acepta `url_imagen` (validar URL http(s) y host de Supabase Storage recomendado), `descripcion`, `imagen_principal`.
  - `PATCH` solo permite `descripcion`, `imagen_principal`.
  - `DELETE` 204; intento sobre id de otra cancha → 404 (no 403, para no filtrar existencia).
- [ ] **T3.6** `GET/POST/PUT/DELETE /api/v1/admin/field/schedules/` (idempotente, `PUT` requiere id).
- [ ] **T3.7** `GET/POST/PATCH/DELETE /api/v1/admin/field/rates/`.
- [ ] **T3.8** `GET /api/v1/admin/field/rates/preview/?fecha=YYYY-MM-DD` → `[{hora_inicio, hora_fin, precio, origen}]`; `fecha` obligatoria (400 si falta o formato inválido).
- [ ] **T3.9** [P] Tests de API por endpoint: happy path, aislamiento entre admins (admin B → 404), validaciones (solape → 409, fecha inválida → 400, principal única → una sola fila con `TRUE`).
- [ ] **ADO:** colección Postman/`http/*.http` con los 7 endpoints; `pytest modules/fields` verde; preview de precios devuelve bloques coherentes con tarifas cargadas.

---

## Iteración 4 — Módulos `bookings` y `finance` (Admin + Dashboard)

### 4.1 Servicios `bookings`

- [ ] **T4.1** `bookings/services.py`:
  - `expire_confirmed_bookings()` → `UPDATE reservas SET estado_reserva='Finalizada' WHERE estado_reserva='Confirmada' AND (fecha_reserva + hora_fin) < now_server` (una sola query, atómica).
  - `list_admin_bookings(cancha, filters)`, `get_admin_booking(cancha, id)`
  - `approve(cancha, id)` → solo desde `Pendiente`; si ya `Confirmada` → 409; si `Finalizada/Cancelada` → 409.
  - `cancel(cancha, id)` → desde `Pendiente|Confirmada`; desde `Finalizada` → 409 (`reserva_ya_finalizada`).
  - `mark_paid(cancha, id)` → set `estado_pago='Pagado'`, `fecha_pago=now()`; si ya pagado → 409 idempotente-opcional (decidir: 200 con no-op vs 409 → **recomendado 409**). Cancelada → 409.
  - Todos mapean `IntegrityError` de exclusión → `409 horario_no_disponible` (carrera entre approve y otra reserva).
- [ ] **T4.2** Hook de expiración: llamar `expire_confirmed_bookings()` al inicio de (a) `bookings` admin views, (b) `finance` dashboard/summary, (c) futura disponibilidad pública. Centralizar en un mixin/decorador `@expire_bookings_first`.
- [ ] **T4.3** [P] Tests: expiración por fecha pasada hoy mismo y ayer, no expira las de hoy +1h; approve/cancel/mark-paid con matriz de estados (tabla de 4×3); cancel libera el slot (crear reserva nueva igual → OK); carrera simulada con dos aprobaciones (mock o `transaction` sequential) → 409.

### 4.2 API `bookings`

- [ ] **T4.4** `GET /api/v1/admin/bookings/` con `django-filter`: `fecha`, `estado_reserva`, `estado_pago`, `q` (ILIKE en `nombre_cliente`, `correo_cliente`, `telefono_cliente`, `codigo_reserva`); paginación + orden `fecha_reserva DESC, hora_inicio`.
- [ ] **T4.5** `GET /api/v1/admin/bookings/{id_reserva}/` (scoped a la cancha del admin).
- [ ] **T4.6** `POST .../approve/`, `POST .../cancel/`, `POST .../mark-paid/` → 200 con reserva serializada actualizada. `cancel` acepta body opcional `{motivo}` → se anexa a `observaciones` (decisión: campo auditoría opcional).
- [ ] **T4.7** [P] Tests de endpoints + aislamiento.

### 4.3 Servicios `finance`

- [ ] **T4.8** `finance/selectors.py` (solo lectura, consume datos de `bookings` mediante `bookings/services` o vistas SQL propias del módulo para no violar frontera):
  - `ingresos_recibidos(cancha, rango)` = SUM(precio_total) WHERE estado_reserva IN ('Confirmada','Finalizada') AND estado_pago='Pagado'.
  - `dinero_pendiente(cancha, rango)` = idem con estado_pago='Pendiente'.
  - `kpis_dashboard(cancha)` = reservas hoy, pendientes de aprobación, confirmadas, canceladas, ingresos, pendiente.
  - `serie_actividad(cancha, días=30)` y `serie_ingresos(cancha, meses=12)`.
  - `requested_approval(cancha)` y `next_matches(cancha)` (Confirmada con fecha+hora futura, límite 5).
- [ ] **T4.9** [P] Tests de agregación: mezcla de las 4 combinaciones estado_reserva × estado_pago; rangos day/week/month/custom (con bordes inclusivos/exclusivos validados contra `America/Bogota`); cancelada excluida; Pendiente de aprobación excluida aunque esté pagada.

### 4.4 API `finance`

- [ ] **T4.10** `GET /api/v1/admin/finance/dashboard/` — devuelve `{kpis, serie_actividad, serie_ingresos, solicitudes_pendientes, proximos_partidos}`. Documentado como ejemplo en `specs/001-admin-panel/contracts/dashboard.schema.json`.
- [ ] **T4.11** `GET /api/v1/admin/finance/summary/?period=day|week|month|custom&start=...&end=...`:
  - `custom` exige `start` y `end` (400 si faltan o `start > end`);
  - retorna `ingresos_recibidos`, `dinero_pendiente`, `total_reservas`, desglose por día e historial de reservas pagadas/pendientes.
- [ ] **ADO:** `pytest modules/bookings modules/finance` verde; comparación manual: dashboard de la mañana = números en DB tras el seed; summary `day` cuadra con dashboard.

---

## Iteración 5 — Frontend Panel de Administrador (React)

### 5.1 Base del frontend

- [ ] **T5.1** `frontend/` con Vite + React + TS, `react-router-dom`, `@tanstack/react-query`, `axios`, `zod`, Tailwind (tokens de Canva: `--color-dark: #0a2328`, `--color-action: #15803d`, `--radius-card`, tarjetas blancas).
- [ ] **T5.2** Cliente Supabase JS (`@supabase/supabase-js`) para login (email/password + Google OAuth), y `apiClient` con interceptor que adjunta `Authorization: Bearer <access_token>` y refresca en `401`.
- [ ] **T5.3** `AuthProvider` + `ProtectedRoute` por rol: `administrador` → panel; `requiere_telefono` → modal bloqueante de teléfono antes de reservar (solo aplica a cliente, pero se deja el guard).
- [ ] **T5.4** Componentes base: `AppShell` (sidebar, header), `Card`, `Table` (con estados loading/empty/error), `Badge` de estado, `Modal`, `DateRangePicker`, `Money(COP)` formatter.

### 5.2 Vistas

- [ ] **T5.5** *Dashboard* → `GET /admin/finance/dashboard/`: 6 KPIs, gráfico actividad + ingresos, solicitudes por aprobar (acciones inline), próximos partidos.
- [ ] **T5.6** *Mi cancha* → `GET/PATCH /admin/field/`: formulario con validación zod y feedback optimista.
- [ ] **T5.7** *Fotografías* → listar/registrar URL (o subir a Supabase Storage desde el navegador y guardar URL pública), marcar principal, eliminar con confirmación.
- [ ] **T5.8** *Horarios* → editor semanal L-D con franjas múltiples; muestra error 409 de solape.
- [ ] **T5.9** *Tarifas* → tabla semanales + sección fecha especial; panel "Vista previa de precios" que consulta `/rates/preview/?fecha=` y muestra bloques con `origen` (base/semanal/especial).
- [ ] **T5.10** *Reservas* → tabla filtrable (fecha, estados, búsqueda), detalle en drawer, acciones aprobar/cancelar/marcar pagado.
- [ ] **T5.11** *Calendario* → vista semanal/diaria con bloques de reservas por estado (Pendiente=amarillo, Confirmada=verde, Cancelada=gris tachado, Finalizada=azul apagado); slot clickeable → detalle.
- [ ] **T5.12** *Contabilidad* → selector day/week/month/custom, tarjetas ingresos/pendiente, desglose e historial paginado.
- [ ] **T5.13** [P] Eliminar de los prototipos los indicadores "Panel demo" y rutas falsas; 404 y sin permisos correctos.
- [ ] **ADO:** login Google y email funcionan contra Supabase; todas las vistas leen datos reales; `npm run build` y `npm run lint` limpios; no hay strings "demo" en el bundle.

---

## Iteración 6 — Endurecimiento y entrega

- [ ] **T6.1** [P] Rate limiting en `/auth/sync/` y login attempts (DRF throttling).
- [ ] **T6.2** [P] Cabeceras CORS restringidas, `DEBUG` desde env, secretos por `.env`, `SECURE_*` para prod.
- [ ] **T6.3** [P] Logging estructurado de cambios de estado de reservas (auditoría mínima en `fecha_creacion`/logs).
- [ ] **T6.4** Cobertura ≥ 85% en `modules/` (medir con `pytest --cov`), excluyendo migraciones.
- [ ] **T6.5** `docs/api.md` generado desde drf-spectacular (o manual) con los contratos §5.
- [ ] **T6.6** Script de despliegue/`Dockerfile` backend + frontend; healthcheck.
- [ ] **ADO:** pipeline local `pytest && ruff && npm run build` en verde; revisión de checklist de seguridad (OWASP top-10 básico).

---

## Riesgos y decisiones

### Decisiones cerradas (2026-11-23)

| ID | Decisión | Implementación |
|----|----------|----------------|
| **R1** | `telefono` **`NULL` en BD** (no bloquea el primer login con Google) pero **obligatorio a nivel de servicio**: en registro tradicional y antes de confirmar cualquier reserva. | T1.4 (`null=True`), T2.5 (validación registro), T2.7 `require_telefono()` → `telefono_requerido`, `/auth/sync/` devuelve `requiere_telefono`. |
| **R4** | **Alineación estricta a horas en punto** (`minute=0, second=0`) en `horarios_operacion`, `tarifas` y `reservas`; duración entera **≥60 min y múltiplo de 60**. | `CheckConstraint` en BD (T1.7, T1.8, T1.9) + validación en serializer (T3.4/T3.7/T3.8) + `PricingEngine` (T3.2). |
| **R5** | `codigo_reserva` = `CY-YYMMDD-` + **4 hex** aleatorios (ej. `CY-240801-A3F2`), `UNIQUE` en BD, **reintento acotado** (máx. 5) ante colisión. | T1.9 (constraint), `bookings/services.create_booking` con reintento. |

### Riesgos abiertos

| ID | Riesgo / decisión | Impacto | Mitigación propuesta |
|----|-------------------|---------|----------------------|
| **R2** | Ranges de `TIME` en PostgreSQL/Django para `ExclusionConstraint` (no hay `timerange` nativo). | Puede requerir SQL manual | Usar `TstzRange`/`Range` sobre `hora_apertura` y `hora_cierre` via `Func`, o migración `RunSQL` con `EXCLUDE USING gist (id_cancha WITH =, dia_semana WITH =, timerange(hora_apertura, hora_cierre) WITH &&)` usando `btree_gist` + función `timerange` custom. Validar en T1.7 antes de seguir. |
| **R3** | Carreras de concurrencia: approve vs nueva reserva. | Doble reserva | La constraint de exclusión parcial es la fuente de verdad; capturar `IntegrityError` y devolver 409. Test T4.3. |
| **R6** | `estado_reserva` como VARCHAR(20) vs. tipo enum Postgres. | Integridad | Preferir `TextChoices` + `CheckConstraint` (portable a Django) en lugar de enum nativo. |
| **R7** | Expiración a `Finalizada` depende de "hora del servidor", pero `USE_TZ` en `America/Bogota`. | Desfase de horas | Definir `expire_confirmed_bookings()` comparando `(fecha + hora_fin)` en TZ local contra `now()` en TZ local, ambos desde `shared/dates.py`. |
| **R8** | `finance` no debe leer `bookings` directamente (frontera). | Acoplamiento | `finance` usa `bookings.services.query_*` como interfaz pública; sin imports de modelos. Alternativa: vistas de solo lectura en `finance`. |
| **R9** | Eliminar imágenes: si se borra la principal, ¿quién lo ve? | UX | Auto-promoción a la más antigua; documentar en `fields/services.py`. |
| **R10** | Multi-franja por día con hueco (08-12, 13-22) y reserva que cruza el hueco (11-14). | Inconsistencia | `PricingEngine`/availability debe exigir que todos los bloques estén dentro de franjas activas; rechazar 400 `fuera_de_horario`. |
| **R11** | Sin endpoint público de disponibilidad/cliente en FASE 1, pero `bookings` necesita `POST` de cliente en FASE 2. | Fuera de alcance | Dejar `bookings/services.create_booking` implementado y testeado en T4.1 aunque la ruta pública llegue después. |
| **R12** | Supabase JWKS: claves rotan; validación HS256 legacy puede romperse. | Auth | Cachear JWKS con TTL y soportar ambos modos por env var. |

---

## Matriz de trazabilidad (spec → tarea)

| Spec § | Requisito | Tareas |
|--------|-----------|--------|
| 2.2 | Estructura módulos | T0.4, T1.1–T1.9 |
| 3.1 | Roles + teléfono (R1 decidido) | T1.4, T2.3, T2.5, T2.7 |
| 3.2 | 1:1 admin-cancha; estado; imagen principal; horarios; tarifas | T1.5–T1.8, T3.1–T3.9 |
| 3.3 | Estados, pagos, transición | T1.9, T4.1–T4.3 |
| 3.4 | Ingresos / pendiente / filtros | T4.8–T4.11 |
| 4 | Esquema + exclusiones | T1.4–T1.12 |
| 5.1 | `/auth/*` | T2.1–T2.8 |
| 5.2 | `/admin/field/*` | T3.4–T3.9 |
| 5.3 | `/admin/bookings/*` | T4.4–T4.7 |
| 5.4 | `/admin/finance/*` | T4.10–T4.11 |
| 6 | Orden de iteraciones | 1→5 = T0…T5 |
