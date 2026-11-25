# Verificación — Iteración 4 (`bookings` + `finance`)

## 1. Transición automática a `Finalizada` y unicidad de `codigo_reserva`

### Expiración (R7)

`modules/bookings/services.py::expire_confirmed_bookings()`

```python
ahora = now_in_tz()                        # America/Bogota, con tzinfo
qs = Reserva.objects.filter(estado_reserva='Confirmada', fecha_reserva__lte=ahora.date())
for reserva in qs:
    fin = make_aware(combine(reserva.fecha_reserva, reserva.hora_fin), tz_negocio)
    if fin < ahora: vencidas.append(pk)
Reserva.objects.filter(pk__in=vencidas).update(estado_reserva='Finalizada')   # 1 sola query
```

- **Solo `Confirmada`**: una `Pendiente` vencida **no** se finaliza (nunca fue aprobada).
- **Comparación en hora local del negocio**, no en hora del contenedor (riesgo que
  detectamos en R7): `fecha_reserva + hora_fin` se reconstruye como datetime
  con la zona `America/Bogota` y se compara con `now_in_tz()`.
- **No bloquea horario**: al pasar a `Finalizada` sale del índice de exclusión
  (que solo cubre `Pendiente`/`Confirmada`), así que la franja queda libre.
- **Cuándo corre**: al inicio de cada consulta del panel —
  `BookingListCreateView`, `BookingDetailView`, `DashboardView`, `SummaryView` —
  y también dentro de `approve()`/`cancel()` antes de validar la transición.

### `codigo_reserva` (R5)

Formato **`CY-YYMMDD-XXXX`** (ej. `CY-261201-A3F2`), 14 caracteres:

```python
ALFABETO = ascii_uppercase + digits          # 36^4 = 1.679.616 combinaciones/día
def generar_codigo_reserva(fecha):
    return f"CY-{fecha:%y%m%d}-{''.join(secrets.choice(ALFABETO) for _ in range(4))}"
```

Unicidad en dos niveles:

1. **BD**: `UNIQUE(codigo_reserva)` + `CHECK ck_reservas_codigo_formato`
   (`^CY-[0-9]{6}-[A-Z0-9]{4}$`) → imposible insertar un código mal formado.
2. **Servicio**: `create_booking()` intenta hasta `INTENTOS_CODIGO = 5` veces.
   Cada intento va en su propio `transaction.atomic()` (savepoint), de modo que
   una colisión de código **no** aborta la transacción externa. Si el
   `IntegrityError` menciona `codigo_reserva`, se reintenta con otro código;
   si menciona `ex_reservas_no_solape`, se traduce a `409 horario_no_disponible`;
   cualquier otro error se propaga. Agotados los 5 intentos → `409 codigo_no_disponible`.

`secrets.choice` (CSPRNG) evita patrones predecibles, algo relevante porque el
código se comparte con el cliente para identificar su reserva.

---

## 2. Reglas de transición de estados

### Máquina de estados (`TRANSICIONES`)

| Origen | Destinos permitidos |
|---|---|
| `Pendiente` | `Confirmada` (aprobar), `Cancelada` (cancelar) |
| `Confirmada` | `Cancelada` (cancelar), `Finalizada` (automático) |
| `Cancelada` | — (terminal) |
| `Finalizada` | — (terminal) |

Cualquier otro par → **`409 estado_invalido`** con `errors.estado_actual`.
Se valida también **después** de la expiración (se hace `refresh_from_db`), así
que aprobar una reserva que venció entre la carga y el clic devuelve
`409` en vez de confirmar una reserva ya terminada.

### Pago presencial (§3.3)

| Regla | Implementación |
|---|---|
| `Pagado` ⇒ `fecha_pago` NOT NULL | `mark_paid()` setea `estado_pago='Pagado'` **y** `fecha_pago=now()` en el mismo `save(update_fields=...)` |
| `Pendiente` ⇒ `fecha_pago` NULL | se crea siempre con `fecha_pago=None`; no existe endpoint que la vacíe |
| Coherencia garantizada | `CHECK ck_reservas_pago_fecha_coherente` en BD (imposible saltárselo por SQL) |
| Reserva `Cancelada` | **no** se puede marcar pagada → `409 estado_invalido` |
| Ya pagada | `409 reserva_ya_pagada` (no opcional) |
| Pago independiente del estado | una `Pendiente` de aprobación **sí** se puede marcar pagada (se paga presencialmente al llegar) |

### Solapes al crear y aprobar (R2 / R10)

| Momento | Protección |
|---|---|
| **Crear** | `calcular_precio()` valida R4 (bloques alineados) y R10 (todo el rango dentro de franjas activas) **antes** de tocar la BD; el `INSERT` choca con `ex_reservas_no_solape` si otro la tomó → `409 horario_no_disponible` |
| **Aprobar** | la constraint cubre `Pendiente` **y** `Confirmada`; como la reserva ya ocupa el horario desde que se crea, aprobar solo cambia la etiqueta. Si aún así hubiera carrera, el `save` atrapa `IntegrityError` → `409 horario_no_disponible` |
| **Cancelar** | sale del índice parcial → la franja queda disponible de inmediato |
| **Cliente sin teléfono** | `require_telefono()` (R1) → `400 telefono_requerido` antes de calcular nada |

R10 en la práctica: con franjas `08-12` y `13-22`, una reserva `11:00–14:00`
se rechaza con `400 fuera_de_horario` porque el bloque 12:00-13:00 no existe.

---

## 3. Dashboard y contabilidad

`modules/finance/selectors.py` — **solo lectura** y **sin importar**
`bookings.models` para agregar (R8: usa el queryset que expone
`bookings.services`). Reglas §3.4:

```
base = reservas de MI cancha con estado_reserva IN ('Confirmada','Finalizada')
ingresos_recibidos = SUM(precio_total) de base WHERE estado_pago = 'Pagado'
dinero_pendiente   = SUM(precio_total) de base WHERE estado_pago = 'Pendiente'
```

- `Pendiente` de aprobación y `Cancelada` **nunca** suman (ni aunque estén pagadas).
- Se usa `Coalesce(Sum(...), 0)` para que un mes sin datos devuelva `0.00`.

| Endpoint | Contenido |
|---|---|
| `GET /admin/finance/dashboard/` | `kpis` (reservas hoy, pendientes/confirmadas/canceladas, por aprobar, ingresos, pendiente), `serie_actividad` (30 días), `serie_ingresos` (6 meses), `solicitudes_por_aprobar`, `proximos_partidos` |
| `GET /admin/finance/summary/?period=day\|week\|month\|custom` | totales del rango, `por_dia` (recibidos/pendientes/reservas) e `historial` |

Rangos en hora local: `day` = hoy; `week` = lunes→domingo ISO; `month` = mes
corriente completo; `custom` exige `start` y `end` (400 si faltan o si
`start > end`).

### Pruebas añadidas

| Archivo | Casos |
|---|---|
| `bookings/tests/test_services.py` | formato y aleatoriedad del código; expiración (vencida, futura, `Pendiente` no expira, hoy terminada, hoy en curso, libera horario); estados (aprobar/cancelar en 8 combinaciones, doble aprobación 409); pago (registra fecha, ya pagada 409, cancelada 409); creación (precio backend, snapshot, solape 409, hueco R10, sin teléfono, **reintento por colisión de código**) |
| `finance/tests/test_finance.py` | matriz 4 estados × 2 pagos con montos; ceros; filtro por rango; aislamiento entre canchas; resolución de los 4 periodos + errores; API de reservas (listado paginado, filtros, detalle, 404 ajeno, approve/cancel/mark-paid, doble approve 409, no puede tocar reservas de otro admin); dashboard (estructura, KPIs del día, solicitudes/próximos, expira antes de responder); summary (day, custom válido/ inválido, period inválido) |

### Criterios de aceptación de la Iteración 4

- [ ] `Confirmada` vencida → `Finalizada` automáticamente en hora local
- [ ] `Pendiente` vencida **no** se finaliza; `Finalizada` libera el horario
- [ ] `codigo_reserva` `CY-YYMMDD-XXXX`, único, con reintento acotado
- [ ] Matriz de transiciones: cualquier par no permitido → `409 estado_invalido`
- [ ] `mark-paid` registra `fecha_pago`; cancelada → 409; doble pago → 409
- [ ] Coherencia `Pagado ⇔ fecha_pago` garantizada por BD
- [ ] Solape al crear → `409 horario_no_disponible`; hueco R10 → `400 fuera_de_horario`
- [ ] Ingresos = Confirmada/Finalizada **y** Pagado; pendiente = idem **y** Pendiente
- [ ] `Cancelada` y `Pendiente` no suman en ninguna métrica
- [ ] Rangos `day/week/month/custom` con errores 400 correctos
- [ ] Todo filtrado por la cancha del admin (404 en reservas ajenas)
- [ ] Suite completa en verde
