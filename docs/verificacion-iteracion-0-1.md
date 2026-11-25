# Verificación — Iteración 0 y 1

Checklist ejecutable de los criterios de aceptación de FASE 1 (estructura + BD).
Todos los comandos se ejecutan desde `canchaya/backend` con el entorno activo
(`.venv\Scripts\python.exe`).

**Nota de credenciales:** no pude ejecutar `migrate` porque el archivo `backend/.env` **no existe en esta máquina** (lo verifiqué con `decouple`, que no encuentra ninguna variable `POSTGRES_*`, y no hay `DATABASE_URL` en el entorno). Cuando esté creado, los comandos de §3/§4/§5 funcionan tal cual.

**Requisito del `.env`:** `backend/.env` con **una** de estas dos formas:

```dotenv
# Opción A (recomendada): URI del Session pooler (puerto 5432)
DATABASE_URL=postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres

# Opción B: variables sueltas
POSTGRES_DB=postgres
POSTGRES_USER=postgres.<ref>
POSTGRES_PASSWORD=<password>
POSTGRES_HOST=aws-0-<region>.pooler.supabase.com
POSTGRES_PORT=5432
```

---

## 1. Requisitos de entorno

| Recurso | Estado requerido | Comprobación |
|---------|------------------|--------------|
| Python 3.12+ | ✅ 3.14.7 | `python --version` |
| PostgreSQL remoto (Supabase) | ✅ PostgreSQL **17.12**, `btree_gist` 1.7 | `scripts/check_db.py` |
| Docker (alternativa local) | ⚠️ no instalado (irrelevante: se usa Supabase) | `docker --version` |
| Dependencias backend | ✅ instaladas en `backend/.venv` | `pip list` |

**URL de conexión:** `aws-1-us-west-2.pooler.supabase.com:5432` (Session pooler), BD `postgres`, esquema `public`.

> **Nota:** las exclusion constraints y `canchaya_timerange()` **solo existen en
> PostgreSQL**. Sin servidor Postgres los tests de BD no pueden ejecutarse.

---

## 2. Comprobaciones estáticas (no requieren BD)

```powershell
cd backend
.\.venv\Scripts\python.exe manage.py check          # "System check identified no issues"
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run   # "No changes detected"
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\black.exe --check .
```

**Esperado:** sin errores. Si `makemigrations --check` detecta cambios, falta
`makemigrations` de algún ajuste de modelo.

---

## 3. Aplicar migraciones desde cero (criterio §1.5 / T1.10)

```powershell
# 1. Crear base de datos
createdb -U canchaya canchaya        # o: docker compose up -d

# 2. Aplicar migraciones
.\.venv\Scripts\python.exe manage.py migrate

# 3. Verificar idempotencia: vuelve a arrancar en una BD limpia
dropdb -U canchaya canchaya_test && createdb -U canchaya canchaya_test
```

**Esperado:** las migraciones aplican en este orden (verificado contra Supabase
PostgreSQL 17.12):

```
contenttypes.0001–0002
auth.0001–0012
users_auth.0001_enable_btree_gist   -> CREATE EXTENSION btree_gist
users_auth.0002_initial             -> usuarios
fields.0001_initial                 -> canchas, imagenes_cancha, horarios_operacion, tarifas
fields.0002_canchaya_timerange      -> CREATE FUNCTION canchaya_timerange
bookings.0001_initial               -> reservas (sin FK a usuarios)
bookings.0002_initial
bookings.0003_initial               -> FK id_cliente + ex_reservas_no_solape
fields.0002_initial                 -> FK id_administrador + exclusiones de horarios y tarifas
sessions.0001_initial
```

> Puntos delicados resueltos:
> - `fields.0002_canchaya_timerange` **debe** ir antes de las exclusiones.
> - Las FKs a `users_auth.Usuario` dependen de `users_auth.0002_initial`, no de
>   `__first__` (que resolvería a la migración de `btree_gist`, sin modelos).
> - No se instala `django.contrib.admin`: evita un ciclo de dependencias con
>   `AUTH_USER_MODEL`. La autorización es por `rol`.

---

## 4. Inspección de constraints en PostgreSQL

### 4.1 Listado de constraints de exclusión

```sql
SELECT conrelid::regclass AS tabla, conname
FROM pg_constraint
WHERE contype = 'x'
ORDER BY 1, 2;
```

**Esperado (exactamente 4 filas):**

| tabla | conname | expresión | condición |
|-------|---------|-----------|-----------|
| `horarios_operacion` | `ex_horarios_no_solape` | `id_cancha WITH =, dia_semana WITH =, canchaya_timerange(hora_apertura,hora_cierre) WITH &&` | `activo` |
| `tarifas` | `ex_tarifas_semanal_no_solape` | `id_cancha WITH =, dia_semana WITH =, canchaya_timerange(hora_inicio,hora_fin) WITH &&` | `dia_semana IS NOT NULL AND activo` |
| `tarifas` | `ex_tarifas_especial_no_solape` | `id_cancha WITH =, fecha_especial WITH =, canchaya_timerange(hora_inicio,hora_fin) WITH &&` | `fecha_especial IS NOT NULL AND activo` |
| `reservas` | `ex_reservas_no_solape` | `id_cancha WITH =, fecha_reserva WITH =, canchaya_timerange(hora_inicio,hora_fin) WITH &&` | `estado_reserva IN ('Pendiente','Confirmada')` |

```sql
-- DDL completo, para copiar a la revisión
SELECT conrelid::regclass, pg_get_constraintdef(oid)
FROM pg_constraint WHERE contype = 'x';
```

### 4.2 Tablas, columnas y checks

```sql
\d+ usuarios
\d+ canchas
\d+ imagenes_cancha
\d+ horarios_operacion
\d+ tarifas
\d+ reservas

-- Todos los CHECK de negocio
SELECT conrelid::regclass AS tabla, conname
FROM pg_constraint WHERE contype = 'c' AND conname LIKE 'ck_%%'
ORDER BY 1, 2;
```

**Checks esperados por tabla:**

| Tabla | Constraints |
|-------|-------------|
| `usuarios` | `ck_usuarios_rol_valido`, `ck_usuarios_nombre_no_vacio` |
| `canchas` | `ck_canchas_precio_base_no_negativo`, `ck_canchas_nombre_no_vacio`, `UNIQUE(id_administrador)` (1:1) |
| `imagenes_cancha` | `uq_imagen_principal_por_cancha` (único parcial), `ck_imagenes_url_http` |
| `horarios_operacion` | `ck_horarios_dia_semana_1_7`, `ck_horarios_rango_positivo`, `ck_horarios_apertura_en_punto`, `ck_horarios_cierre_en_punto` |
| `tarifas` | `ck_tarifas_semanal_xor_especial`, `ck_tarifas_dia_semana_1_7`, `ck_tarifas_rango_positivo`, `ck_tarifas_inicio_en_punto`, `ck_tarifas_fin_en_punto`, `ck_tarifas_precio_positivo` |
| `reservas` | `ck_reservas_estado_valido`, `ck_reservas_estado_pago_valido`, `ck_reservas_pago_fecha_coherente`, `ck_reservas_rango_positivo`, `ck_reservas_inicio_en_punto`, `ck_reservas_fin_en_punto`, `ck_reservas_precio_no_negativo`, `ck_reservas_codigo_formato`, `UNIQUE(codigo_reserva)` |

### 4.3 Función R2 y extensión

```sql
SELECT canchaya_timerange('08:00'::time, '10:00'::time);   -- [28800,36000)
SELECT extname FROM pg_extension WHERE extname = 'btree_gist';
```

### 4.4 Prueba manual del solape de reservas

```sql
-- 1. Insertar pendiente 08:00-10:00 -> OK
-- 2. Insertar pendiente 09:00-11:00 -> ERROR: conflicting key value violates exclusion constraint
-- 3. La misma insertada como 'Cancelada' -> OK
```

---

## 5. Suite de tests (criterio T1.11)

```powershell
cd backend
$env:PYTHONPATH = (Get-Location).Path     # necesario para scripts/
.\.venv\Scripts\python.exe -m pytest -q --create-db
```

`conftest.py` (`pytest_configure`) **elimina y recrea** `test_<DB>` en cada
corrida, porque el Session pooler de Supabase deja sesiones colgadas y Django
fallaría con `database "test_postgres" is being accessed by other users`.
Si la limpieza falla, el propio hook aborta con un mensaje claro en lugar de un
`SystemExit: 2`.

Limpieza manual (si hace falta fuera de pytest):

```powershell
.\.venv\Scripts\python.exe scripts\test_db.py status
.\.venv\Scripts\python.exe scripts\test_db.py drop
```

Tests que validan los criterios:

| Archivo | Cubre |
|---------|-------|
| `shared/tests/test_infra.py` | `btree_gist`, `canchaya_timerange`, **las 4 constraints `ex_*`**, rutas §5 montadas, health |
| `shared/tests/test_validators.py` | R4: horas en punto, duración ≥60 y múltiplo de 60 |
| `modules/fields/tests/test_constraints.py` | 1:1 cancha, imagen principal única, solapes de horarios y tarifas, XOR semanal/especial |
| `modules/bookings/tests/test_constraints.py` | solape de reservas por estado, coherencia pago/fecha, formato de código, `telefono` nullable (R1) |

**Criterio de aceptación:** `0 failed`. Resultado actual: **58 passed**.

> Detalle técnico: la base de test (`test_postgres`) se crea vacía y sin
> extensiones, por lo que `conftest.py` (`pytest_configure`) habilita
> `btree_gist` antes de migrar. Antes de cada corrida conviene liberar la base:
> `python scripts/test_db.py drop` y luego `pytest --create-db`.

---

## 6. Criterios de aceptación — resumen

### Iteración 0

- [x] Repo con `.gitignore`, `.editorconfig`, `docker-compose.yml`, `.env.example`
- [x] `DOC` estructura `backend/{config,shared,modules}` con `__init__.py`
- [x] `pytest` configurado (`pyproject.toml`), `ruff` + `black` configurados
- [ ] `docker compose up -d` → **bloqueado**: Docker no instalado

### Iteración 1

- [x] Settings modulares (`base`/`dev`/`prod`/`test`), TZ `America/Bogota`, DRF con
      autenticación Supabase, paginación y handler de errores
- [x] `/api/v1/` con los 4 módulos y todas las rutas de §5 montadas
- [x] Modelos de las 6 tablas con `db_table` según la spec
- [x] `btree_gist` + `canchaya_timerange()` + 4 exclusion constraints + checks
      **verificados en Supabase** (`scripts/report_constraints.py`)
- [x] Seed `seed_field_admin` idempotente (ejecutado 2× sin duplicar)
- [x] `migrate` desde cero aplicado sobre Supabase PostgreSQL 17.12
- [x] `pytest` → **58 passed**
- [x] `ruff` + `black` + `manage.py check` limpios

### Cómo rehacer la BD desde cero (dev)

```powershell
cd backend
$env:PYTHONPATH = (Get-Location).Path
.\.venv\Scripts\python.exe scripts\reset_public.py --yes   # solo esquema public
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_field_admin
.\.venv\Scripts\python.exe -m pytest -q
```

### Scripts de operación (`backend/scripts/`)

| Script | Uso |
|--------|-----|
| `check_env.py` | Forma del `.env` sin exponer secretos (detecta placeholders) |
| `check_db.py` | Conexión, versión, permisos `CREATEDB`, extensiones |
| `inspect_public.py` | Inventario rápido de `public` antes de migrar |
| `dump_schema.py` | Columnas, constraints e índices de las 6 tablas |
| `report_constraints.py` | Reporte de aceptación: exclusiones, únicos, checks, FKs |
| `reset_public.py` | Borra solo `public` (nunca `auth` de Supabase); aborta si hay usuarios |
| `drop_legacy_public.py` | Retira el esquema manual previo si sus tablas están vacías |
