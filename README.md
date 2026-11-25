# canchaya.

Plataforma web para buscar, consultar disponibilidad y reservar canchas de fútbol.
Esta entrega corresponde a la **FASE 1**: backend, base de datos y panel del
administrador (propietario de una cancha).

**Stack:** Django 5 + DRF · PostgreSQL 17 (Supabase) · React 18 + Vite + React Query · Supabase Auth.

---

## Estructura

```text
canchaya/
├── backend/               Django (monolito modular)
│   ├── config/settings/   base · dev · prod · test
│   ├── shared/            excepciones, JWT Supabase, permisos, utilidades
│   ├── modules/
│   │   ├── users_auth/    usuarios, roles, aprovisionamiento
│   │   ├── fields/        cancha, fotos, horarios, tarifas, PricingEngine
│   │   ├── bookings/      reservas, estados, expiración
│   │   └── finance/       dashboard y contabilidad (solo lectura)
│   └── scripts/           diagnóstico y operación
├── frontend/              Panel React del administrador
├── docs/                  verificación por iteración, despliegue, entorno
├── specs/                 especificación SDD y plan de tareas
└── docker-compose*.yml    desarrollo (db) y producción (todo)
```

---

## Puesta en marcha (Windows / PowerShell)

> `npm.ps1` suele estar bloqueado por la *Execution Policy*. Si `npm` falla,
> usa `cmd /c "npm ..."`.

### 1. Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

Copy-Item .env.example .env
#  Edita .env: DATABASE_URL (Session pooler de Supabase, puerto 5432),
#              SUPABASE_URL y SUPABASE_JWT_SECRET (si el proyecto usa HS256).

$env:PYTHONPATH = (Get-Location).Path
.\.venv\Scripts\python.exe scripts\check_env_local.py   # diagnóstico
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_field_admin   # cancha demo (opcional)
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

API: <http://127.0.0.1:8000/api/v1/health/> · contrato: <http://127.0.0.1:8000/api/v1/schema/>

### 2. Frontend

```powershell
cd frontend
Copy-Item .env.example .env
#  Edita .env: VITE_SUPABASE_URL y VITE_SUPABASE_ANON_KEY (anon/publishable).

cmd /c "npm install"
cmd /c "npm run dev"      # http://localhost:5173
```

### 3. Administrador

Las cuentas de administrador **no** se registran públicamente:

1. Crea el usuario en Supabase → *Authentication → Users*.
2. Copia su **User UID** y ejecuta:

```powershell
cd backend
$env:PYTHONPATH = (Get-Location).Path
.\.venv\Scripts\python.exe manage.py aprovisionar_admin `
    --correo "dueno@cancha.com" --uid "<USER_UID>" `
    --cancha "Mi Cancha" --direccion "Calle 1 # 2-3"
```

---

## Comandos habituales

| Comando | Uso |
|---|---|
| `manage.py check` | validación estática de Django |
| `manage.py makemigrations --check --dry-run` | detectar modelos sin migración |
| `pytest` | suite completa (**238 tests**) |
| `pytest --cov` | cobertura (**91 %**) |
| `ruff check .` · `black --check .` | linters |
| `cmd /c "npm run test"` | 39 tests del frontend |
| `cmd /c "npm run build"` | build de producción |
| `manage.py check --deploy` | chequeos de seguridad (usar `config.settings.prod`) |

> La base de test se recrea al inicio de cada corrida (`conftest.py`), porque el
> Session pooler deja sesiones colgadas.

---

## Reglas de negocio clave

- **R4** — bloques exactos de 60 min (horas en punto), garantizado en BD y serializers.
- **R2** — sin solapes: `btree_gist` + `EXCLUDE USING gist` sobre rangos de tiempo.
- **R10** — una reserva no puede cruzar un hueco entre franjas de atención.
- **R1** — `telefono` nullable en BD, obligatorio antes de reservar.
- **R5** — `codigo_reserva` `CY-YYMMDD-XXXX` único, con reintento acotado.
- **R7** — la expiración a `Finalizada` compara en hora de `America/Bogota`.
- **R8** — `finance` no importa modelos de `bookings` (frontera de módulos).

---

## Documentación

| Documento | Contenido |
|---|---|
| `specs/001-admin-panel/tasks.md` | plan SDD, riesgos y decisiones |
| `docs/verificacion-iteracion-{0-1,2,3,4,5,6}.md` | criterios de aceptación por fase |
| `docs/entorno-local-login.md` | probar el login real contra Supabase |
| `docs/despliegue.md` | Docker, nginx y checklist de producción |
