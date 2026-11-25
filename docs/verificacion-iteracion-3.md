# Verificación — Iteración 3 (Módulo `fields`)

## 1. Cómo implementa el `PricingEngine` la prioridad, R4, R2 y R10

Archivo: `backend/modules/fields/services_pricing.py`

### Prioridad de tarifas (§3.2)

La prioridad **no** se resuelve "eligiendo una tarifa para la reserva", sino
**bloque por bloque de 60 minutos**:

```python
def _tarifa_de_bloque(tarifas, fecha, inicio):
    especial = <tarifa activa con fecha_especial == fecha y hora_inicio <= inicio < hora_fin>
    if especial: return especial          # 1º  Fecha Especial
    dia = fecha.isoweekday()
    return <tarifa activa con dia_semana == dia y hora_inicio <= inicio < hora_fin>
                                          # 2º  Tarifa Semanal
    # si no hay ninguna -> 3º Precio Base de la cancha
```

Consecuencias verificadas:

| Caso | Resultado |
|------|-----------|
| Sin tarifas | todos los bloques a `precio_base`, origen `base` |
| Tarifa semanal 08-10 en martes | 08:00 y 09:00 → semanal (80.000); 10:00+ → base |
| Tarifa especial 09-11 el 24-dic | 09:00 y 10:00 → especial (95.000), aunque haya semanal |
| Tarifa `activo=False` | se ignora |
| Tarifa de otro día | no aplica |
| Rango 08-10 con dos orígenes | **suma** de bloques: 70.000 + 60.000 = 130.000 |

El rango se descompone con `while cursor < limite` en saltos exactos de
1 hora, y `calcular_precio()` devuelve `(total, [Bloque])` para que el llamador
pueda auditar el desglose.

### R4 — bloques alineados a 60 minutos

Tres capas de defensa:

| Capa | Dónde | Comportamiento |
|------|-------|----------------|
| **BD** | `CheckConstraint` `ck_horarios_*_en_punto`, `ck_tarifas_*_en_punto`, `ck_reservas_*_en_punto` | minuto = 0 y segundo = 0, imposible saltárselo incluso por SQL |
| **Serializer** | `_validar_hora_en_punto()` | `400` con `code: bloque_no_alineado` |
| **Servicio** | `assert_valid_booking_range()` de `shared/validators.py` | duración ≥ 60 y múltiplo de 60 → `400 duracion_invalida` |

### R2 — sin solapamientos

Dos niveles:

1. **BD (fuente de verdad)**: cuatro `ExclusionConstraint` con
   `btree_gist` + función propia `canchaya_timerange(start, end)` → `int4range`
   `[inicio, fin)` en segundos:

   | Constraint | Condición |
   |------------|-----------|
   | `ex_horarios_no_solape` | `activo` |
   | `ex_tarifas_semanal_no_solape` | `dia_semana IS NOT NULL AND activo` |
   | `ex_tarifas_especial_no_solape` | `fecha_especial IS NOT NULL AND activo` |
   | `ex_reservas_no_solape` | `estado_reserva IN ('Pendiente','Confirmada')` |

2. **Servicio**: `add_schedule`/`update_schedule` y `add_rate`/`update_rate`
   capturan el `IntegrityError` y lo traducen a `409 horario_solapado` /
   `409 tarifa_solapada`, en lugar de exponer un 500.

   Franjas **contiguas** (`08-12` y `12-14`) se permiten: el rango es
   semiabierto, así que no se solapan en el borde.

### R10 — huecos entre franjas

`calcular_precio()` exige que **cada bloque** esté contenido en una franja
activa (`hora_apertura <= inicio and fin <= hora_cierre`). Con franjas
`08-12` y `13-22`:

- `08:00–12:00` → ✅ 4 bloques
- `11:00–14:00` → ❌ `400 fuera_de_horario` (el bloque 12:00-13:00 no existe)
- `21:00–23:00` → ❌ (pasa del cierre)
- día sin franja (domingo) → ❌ `400 fuera_de_horario`

---

## 2. Protección de los endpoints del panel (`IsFieldAdmin`)

Todas las vistas heredan de `MiCanchaAPIView`, que declara el permiso:

```python
class MiCanchaAPIView(APIView):
    permission_classes = [IsFieldAdmin]
```

Y `IsFieldAdmin` (`shared/permissions.py`) resuelve:

| Situación | Respuesta |
|---|---|
| Sin token / token inválido | `401` + `WWW-Authenticate: Bearer realm="api"` |
| Autenticado, rol ≠ administrador | `403 {"code":"rol_requerido"}` |
| Administrador **sin cancha** | `403 {"code":"admin_sin_cancha"}` |
| Administrador con su cancha | `200`, con `request.cancha` disponible |

**Relación 1:1**: la cancha se obtiene de `fields.services.get_cancha_by_admin(request.user)`
y se guarda en `request.cancha`. Las vistas no aceptan `id_cancha` en body ni en
URL; los recursos hijos se buscan **siempre** con
`self.cancha.imagenes.filter(pk=...)`, `self.cancha.horarios.filter(...)`, etc.
Un id de otra cancha devuelve **404** (no revela existencia) y, si se duplica
un admin, la BD lo impide (`UNIQUE(id_administrador)`).

Endpoints protegidos:

| Método | Ruta | Regla adicional |
|---|---|---|
| `GET/PATCH` | `/api/v1/admin/field/` | solo su cancha |
| `GET/POST` | `/api/v1/admin/field/images/` | la 1.ª imagen es principal automáticamente |
| `PATCH/DELETE` | `/api/v1/admin/field/images/{id}/` | marcar principal desmarca la anterior; borrar la principal promueve la más antigua |
| `GET/POST` | `/api/v1/admin/field/schedules/` | `409` si se solapa |
| `PUT/PATCH/DELETE` | `/api/v1/admin/field/schedules/{id}/` | `409` si el cambio solapa |
| `GET/POST` | `/api/v1/admin/field/rates/` | semanal XOR especial; `409` si solapa |
| `PATCH/DELETE` | `/api/v1/admin/field/rates/{id}/` | idem |
| `GET` | `/api/v1/admin/field/rates/preview/?fecha=` | bloques del día con `origen` |
| `GET` | `/api/v1/admin/field/rates/quote/?fecha=&inicio=&fin=` | precio total de un rango (apoyo a la Iteración 4) |

---

## 3. Pruebas añadidas y criterios de aceptación

### `modules/fields/tests/test_pricing.py`

| Grupo | Casos |
|---|---|
| **Prioridad** | base sin tarifas; semanal pisa base; no aplica otro día; **especial pisa semanal**; tarifa inactiva ignorada; día sin horario → sin bloques |
| **Suma de bloques** | 2 h mixtas (130.000); rango de 3 h |
| **R4** | 3 rangos desalineados (08:00-08:30, 08:15-09:00, 08:00-09:45); duración 0; 1 h exacta válida |
| **R10** | rango que cruza el hueco; antes de abrir; pasando el cierre; día sin operación; franja inactiva; rango completo 4 bloques |

### `modules/fields/tests/test_api.py`

| Grupo | Casos |
|---|---|
| **Mi cancha** | GET; PATCH múltiple; nombre vacío 400; precio negativo 400 |
| **Aislamiento** | **admin sin cancha → 403 `admin_sin_cancha`**; cliente → 403 `rol_requerido`; sin token → 401 con reto; admin B no ve ni borra recursos de A (4 recursos, 404 y verificación de que siguen existiendo) |
| **Fotos** | 1.ª imagen principal automática; marcar principal desmarca la anterior (1 sola en BD); URL no http 400; borrar principal promueve la más antigua; editar descripción |
| **Horarios** | crear/listar; solape 409; contiguas 201; hora no en punto 400; cierre < apertura 400; día 9 → 400; PUT + DELETE; PUT que genera solape → 409 |
| **Tarifas** | semanal; especial; XOR (ni uno / ambos) → 400; solape 409; especial + semanal conviven; precio 0 → 400; PATCH + DELETE |
| **Preview** | prioridades combinadas (semanal/especial/base en el mismo día); sin fecha 400; fecha inválida 400; día sin horario → `[]` |
| **Quote** | cotiza rango; hueco → 400 `fuera_de_horario`; parámetros inválidos 400 |

### Criterios de aceptación de la Iteración 3

- [ ] `PATCH /admin/field/` solo modifica la cancha del admin autenticado
- [ ] Máximo **una** imagen principal, garantizada por BD e índices parciales
- [ ] Borrar la principal promueve la más antigua (R9 documentado)
- [ ] Horarios solapados → `409 horario_solapado`; contiguos permitidos
- [ ] Horas no alineadas → `400` en serializer y en BD
- [ ] Tarifas: semanal XOR especial; solape → `409 tarifa_solapada`
- [ ] `PricingEngine`: especial > semanal > base, bloque a bloque, sumando
- [ ] Rango en hueco/fuera de horario → `400 fuera_de_horario` (R10)
- [ ] `rates/preview/` devuelve bloques con `origen` correcto
- [ ] Admin sin cancha → `403 admin_sin_cancha`; cliente → `403 rol_requerido`; sin token → `401`
- [ ] Ningún endpoint permite operar sobre la cancha de otro admin (404)
- [ ] Suite completa (`pytest`) en verde
