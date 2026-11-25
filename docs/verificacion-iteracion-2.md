# Verificación — Iteración 2 (Auth Supabase, roles y aislamiento 1:1)

## 1. Endpoints y clases añadidas

### Endpoints (§5.1)

| Método | Ruta | Vista | Auth | Respuesta |
|--------|------|-------|------|-----------|
| `POST` | `/api/v1/auth/sync/` | `modules.users_auth.api.views.SyncView` | **Bearer token obligatorio** (valida JWT directamente, sin exigir perfil previo) | `200` perfil + `rol` + `requiere_telefono` + `creado` |
| `GET` | `/api/v1/auth/me/` | `MeView` | `IsAuthenticated` (JWT) | `200` perfil |
| `PATCH` | `/api/v1/auth/me/` | `MeView` | `IsAuthenticated` (JWT) | `200` perfil actualizado |

> Se añadió `GET /auth/me/` (T2.4), que la spec §5.1 no listaba pero el frontend
> necesita para el guard de rol y para saber si falta el teléfono.

### Autenticación — `shared/auth/`

| Clase / función | Rol |
|-----------------|-----|
| `supabase.verificar_token(token)` | Valida firma, `exp`, `aud` y `iss`; devuelve `ClaimsToken(sub, correo, nombre, crudo)`. |
| `_CacheJWKS` | Cachea el JWKS con TTL (`SUPABASE_JWKS_CACHE_TTL`) y refresca si aparece un `kid` desconocido (rotación de claves). |
| `SupabaseJWTAuthentication` | Autenticador DRF por defecto (en `REST_FRAMEWORK`). Extrae `Bearer`, valida, resuelve el perfil y rechaza inactivos. |
| `CredencialesInvalidas` | `AuthenticationFailed` con `code` (`token_expirado`, `token_invalido`, `perfil_no_sincronizado`…). |

**Soporte dual de algoritmo:**

```
alg = HS256  -> firma con SUPABASE_JWT_SECRET            (proyectos legacy)
alg = RS256  -> clave pública del JWKS de SUPABASE_URL   (proyectos nuevos)
otro alg     -> 401 token_invalido
```

### Servicio de usuarios — `modules/users_auth/services.py`

| Función | Uso |
|---------|-----|
| `sync_usuario(claims)` | Crea el perfil como `cliente` o vincula el preexistente por correo; idempotente; nunca degrada un rol. |
| `resolver_usuario_autenticado(claims)` | Búsqueda por `supabase_uid` con vinculación por correo para perfiles aprovisionados. |
| `update_perfil(usuario, datos)` | `nombre`/`telefono`; rechaza `rol`, `activo`, `correo`, `supabase_uid` con `campo_no_permitido`. |
| `normalizar_telefono(valor)` | Valida celular CO y normaliza a `+57XXXXXXXXXX`. |
| `require_telefono(usuario)` | **R1**: lanza `telefono_requerido` antes de confirmar reservas. |
| `aprovisionar_admin(...)` | Opción A: promueve/crea administrador y vincula `supabase_uid`. |

### Permiso `IsFieldAdmin` (frontera 1:1)

```python
def has_permission(self, request, view):
    usuario = get_usuario(request)
    if usuario is None or usuario.rol != Rol.ADMINISTRADOR:
        return False                      # 403 "Se requiere rol administrador."
    cancha = fields_services.get_cancha_by_admin(usuario)   # 1:1 por FK UNIQUE
    if cancha is None:
        request.admin_sin_cancha = True
        return False                      # 403 "sin cancha asignada"
    request.cancha = cancha               # la vista NUNCA elige la cancha
    return True
```

Claves del aislamiento:

1. **Fuente de la cancha**: la vista no recibe `id_cancha` por URL ni query; solo
   usa `request.cancha`, resuelta desde `request.user`.
2. **Garantía de unicidad en BD**: `canchas.id_administrador` es `UNIQUE`
   (relación 1:1), así que no puede existir una segunda cancha para un admin.
3. **Frontera de módulos**: `shared/` no importa `modules.fields.models`, usa
   `modules.fields.services.get_cancha_by_admin`.
4. **Admin sin cancha**: 403 explícito (`admin_sin_cancha`), no una lista vacía.

---

## 2. Casos que cubren los tests de la Iteración 2

### `shared/tests/test_auth_jwt.py` — verificación del token

| Grupo | Casos |
|-------|-------|
| **RS256** | token válido; expirado; firma inválida (otra clave, mismo `kid`); `aud` incorrecta; `iss` incorrecto; `kid` desconocido; sin `SUPABASE_URL` |
| **HS256** | token válido; secreto incorrecto |
| **Formato** | token vacío; token basura; algoritmo no soportado (HS384) |
| **Autenticación DRF** | sin encabezado → `None` (anónimo); encabezado mal formado; usuario existente; perfil no sincronizado → `401 perfil_no_sincronizado`; cuenta desactivada → `403 cuenta_desactivada`; vinculación por correo conservando rol y nombre |

### `modules/users_auth/tests/test_auth_api.py` — endpoints y negocio

| Grupo | Casos |
|-------|-------|
| **`/auth/sync/`** | crea `cliente` por defecto + `requiere_telefono=True`; idempotente (`creado: false`, sin duplicados); actualiza nombre desde Supabase; **no** sobrescribe rol existente; vincula perfil aprovisionado por correo; sin token → 401; token expirado → 401 `token_expirado`; cuenta desactivada → 403 |
| **`/auth/me/`** | `GET` perfil; sin auth → 401; `PATCH` nombre + teléfono (normalizado a `+57…`); 4 teléfonos inválidos → 400 `telefono_invalido`; teléfono vacío lo limpia y vuelve a `requiere_telefono`; 4 campos protegidos → 400 `campo_no_permitido`; body vacío → 400 |
| **`IsFieldAdmin`** | admin con cancha pasa y expone `request.cancha`; es **su** cancha y no otra; admin sin cancha → `admin_sin_cancha`; cliente rechazado; anónimo rechazado |
| **Aprovisionamiento** | crea admin nuevo + cancha; promueve cliente existente; vincula el seed por correo; `uid` duplicado → `CommandError`; sin uid ni perfil → `CommandError`; teléfono inválido → `CommandError` |
| **`require_telefono`** | cliente de Google sin teléfono → `telefono_requerido`; con teléfono → pasa |

### `modules/fields/tests/test_permissions.py` — aislamiento 1:1

| Caso |
|------|
| Cada admin obtiene **su** cancha (y difiere de la del otro) |
| Admin sin cancha deja `admin_sin_cancha` en el request |
| Cliente y anónimo rechazados |
| La cancha es un objeto único, no una colección (`1:1` en BD) |

---

## 3. Prueba de punta a punta del aprovisionamiento del administrador

### Paso a paso

```powershell
cd backend
$env:PYTHONPATH = (Get-Location).Path
```

**1. Crear el usuario en Supabase Auth**

*Supabase → Authentication → Users → Add user* (email + contraseña) o invitar con
Google. Copiar la columna **User UID** (UUID).

**2. Vincularlo como administrador**

```powershell
# Admin existente en BD (p. ej. el del seed), solo hay que vincular su uid:
.\.venv\Scripts\python.exe manage.py aprovisionar_admin `
    --correo "propietario@canchaya.test" `
    --uid "<USER_UID_DE_SUPABASE>"

# Admin nuevo, creando también su cancha:
.\.venv\Scripts\python.exe manage.py aprovisionar_admin `
    --correo "dueno@cancha.com" `
    --uid "<USER_UID>" `
    --nombre "Dueño Cancha" `
    --telefono 3001234567 `
    --cancha "Cancha La Jugada" `
    --direccion "Calle 45 # 12-30"
```

Salida esperada:

```
Administrador listo: propietario@canchaya.test (rol=administrador, uid=...)
Cancha actual: Cancha La Jugada (id=1)
```

**3. Obtener el access token** desde el frontend (SDK de Supabase) o con curl:

```powershell
curl -X POST "$env:SUPABASE_URL/auth/v1/token?grant_type=password" `
  -H "apikey: <ANON_KEY>" -H "Content-Type: application/json" `
  -d '{"email":"propietario@canchaya.test","password":"..."}'
```

**4. Sincronizar el perfil y comprobar el rol**

```powershell
curl -X POST http://localhost:8000/api/v1/auth/sync/ -H "Authorization: Bearer <TOKEN>"
# -> {"rol":"administrador","requiere_telefono":false,"creado":false,...}

curl http://localhost:8000/api/v1/auth/me/ -H "Authorization: Bearer <TOKEN>"
```

**5. Negative checks** (verifican el aislamiento)

```powershell
# Token de un cliente -> 403 "Se requiere rol administrador" en /api/v1/admin/field/
# Token inválido/expirado -> 401 token_invalido / token_expirado
# Sin token            -> 401
```

### Criterios de aceptación de la Iteración 2

- [x] `/auth/sync/` crea el perfil `cliente` con `requiere_telefono` según `telefono`
- [x] `/auth/sync/` es idempotente y **no** modifica `rol` existente
- [x] `/auth/me/` devuelve el perfil y permite `PATCH nombre/telefono`
- [x] `PATCH /auth/me/` rechaza `rol`, `activo`, `correo`, `supabase_uid` con `campo_no_permitido`
- [x] Teléfono inválido → `400 telefono_invalido`; vacío → `null` + `requiere_telefono=true`
- [x] Token expirado → `401 token_expirado`; cuenta inactiva → `403 cuenta_desactivada`
- [x] Perfil inexistente → `401 perfil_no_sincronizado`
- [x] `IsFieldAdmin` solo deja pasar administradores activos **con** cancha y expone `request.cancha` (1:1)
- [x] `aprovisionar_admin` vincula un usuario de Supabase Auth y le asigna el rol
- [x] `pytest` completo en verde (Iteración 1 + 2)

---

## Anexo — hallazgos técnicos (no obvios) documentados

| # | Hallazgo | Consecuencia | Solución aplicada |
|---|----------|--------------|-------------------|
| 1 | `APIView.handle_exception` **sobrescribe** `exc.auth_header` con el reto de la **vista**; una vista sin `authentication_classes` convierte todo 401 en 403 | `/auth/sync/` sin token devolvía 403 | `PublicAPIView` usa `SoloRetoBearer` (no autentica, pero aporta `WWW-Authenticate`) |
| 2 | En pyjwt 2.15 `issuer` **no** se lee de `options`; sin el kwarg, `verify_iss` pasa siempre | Tokens con `iss` ajeno aceptados (riesgo de seguridad) | `issuer=` se pasa como kwarg junto con `verify_iss=True` |
| 3 | `UNAUTHENTICATED_USER = None` **rompe** el 401 (es `None`, la condición `is_authenticated` explota y el reto no se emite) | 500 en endpoints autenticados | Se eliminó el setting |
| 4 | El handler DRF devuelve `code="authentication_failed"` aunque la excepción traiga `code` | Frontend no distinguía `token_expirado` | `_codigo()` prioriza `exc.code` propio |
| 5 | `ValidationError` de un serializer se dispara antes de la validación de negocio | `supabase_uid: "x@y.co"` daba `invalid` en vez de `campo_no_permitido` | El campo se define como `CharField` |
