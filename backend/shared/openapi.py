"""Esquema OpenAPI 3.1 escrito a mano (T6.5).

Se genera sin dependencias extra (`drf-spectacular` añadiría otra capa) y se
sirve en `GET /api/v1/schema/` para publicarlo o importarlo en Postman/Insomnia.

Los tipos son la fuente de verdad del contrato; si cambia un serializer hay que
actualizar este archivo en el mismo commit.
"""

from __future__ import annotations

from django.http import JsonResponse

_BEARER = {"bearerAuth": []}

_ERROR = {
    "type": "object",
    "properties": {
        "code": {"type": "string", "example": "rol_requerido"},
        "detail": {"type": "string"},
        "errors": {"type": "object", "additionalProperties": True},
    },
    "required": ["code", "detail"],
}

_RESPUESTAS_ERROR = {
    "400": {
        "description": "Datos inválidos",
        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}},
    },
    "401": {
        "description": "Token ausente, expirado o inválido",
        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}},
    },
    "403": {
        "description": "Rol insuficiente o admin sin cancha",
        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}},
    },
    "404": {
        "description": "Recurso inexistente en la cancha del admin",
        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}},
    },
    "409": {
        "description": "Conflicto de estado o solape",
        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}},
    },
    "429": {
        "description": "Demasiadas peticiones (throttle)",
        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}},
    },
}

SCHEMA: dict = {
    "openapi": "3.1.0",
    "info": {
        "title": "canchaya. API — FASE 1",
        "version": "1.0.0",
        "description": (
            "Backend del panel de administrador. Autenticación por JWT de Supabase "
            "(`Authorization: Bearer <access_token>`). Todos los endpoints `/admin/*` "
            "operan exclusivamente sobre la cancha del administrador autenticado (1:1)."
        ),
    },
    "servers": [{"url": "/api/v1", "description": "API v1"}],
    "components": {
        "securitySchemes": {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT (Supabase)",
            }
        },
        "schemas": {
            "Error": _ERROR,
            "Usuario": {
                "type": "object",
                "properties": {
                    "id_usuario": {"type": "integer"},
                    "supabase_uid": {"type": "string", "format": "uuid"},
                    "nombre": {"type": "string", "maxLength": 120},
                    "correo": {"type": "string", "format": "email"},
                    "telefono": {
                        "type": ["string", "null"],
                        "maxLength": 30,
                        "example": "+573001112233",
                    },
                    "rol": {"type": "string", "enum": ["cliente", "administrador"]},
                    "activo": {"type": "boolean"},
                    "requiere_telefono": {"type": "boolean"},
                    "fecha_creacion": {"type": "string", "format": "date-time"},
                    "creado": {"type": "boolean", "description": "Solo en /auth/sync/"},
                },
            },
            "Cancha": {
                "type": "object",
                "properties": {
                    "id_cancha": {"type": "integer"},
                    "nombre": {"type": "string", "maxLength": 150},
                    "direccion": {"type": "string", "maxLength": 250},
                    "zona": {"type": ["string", "null"], "maxLength": 100},
                    "descripcion": {"type": "string"},
                    "precio_base": {"type": "string", "example": "60000.00"},
                    "estado": {"type": "boolean"},
                    "fecha_creacion": {"type": "string", "format": "date-time"},
                },
            },
            "Imagen": {
                "type": "object",
                "properties": {
                    "id_imagen": {"type": "integer"},
                    "url_imagen": {"type": "string", "format": "uri"},
                    "descripcion": {"type": "string", "maxLength": 250},
                    "imagen_principal": {"type": "boolean"},
                    "fecha_creacion": {"type": "string", "format": "date-time"},
                },
            },
            "Horario": {
                "type": "object",
                "properties": {
                    "id_horario": {"type": "integer"},
                    "dia_semana": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 7,
                        "description": "1=lunes … 7=domingo",
                    },
                    "hora_apertura": {
                        "type": "string",
                        "example": "08:00:00",
                        "description": "Debe ser HH:00:00 (R4)",
                    },
                    "hora_cierre": {"type": "string", "example": "12:00:00"},
                    "activo": {"type": "boolean"},
                },
            },
            "Tarifa": {
                "type": "object",
                "properties": {
                    "id_tarifa": {"type": "integer"},
                    "dia_semana": {"type": ["integer", "null"], "minimum": 1, "maximum": 7},
                    "fecha_especial": {"type": ["string", "null"], "format": "date"},
                    "hora_inicio": {"type": "string", "example": "08:00:00"},
                    "hora_fin": {"type": "string", "example": "10:00:00"},
                    "precio_hora": {"type": "string", "example": "70000.00"},
                    "activo": {"type": "boolean"},
                    "origen": {"type": "string", "enum": ["semanal", "especial"], "readOnly": True},
                },
                "description": "Exactamente uno de dia_semana o fecha_especial (XOR).",
            },
            "BloquePrecio": {
                "type": "object",
                "properties": {
                    "hora_inicio": {"type": "string", "example": "08:00"},
                    "hora_fin": {"type": "string", "example": "09:00"},
                    "precio": {"type": "string", "example": "70000.00"},
                    "origen": {"type": "string", "enum": ["base", "semanal", "especial"]},
                },
            },
            "Reserva": {
                "type": "object",
                "properties": {
                    "id_reserva": {"type": "integer"},
                    "codigo_reserva": {
                        "type": "string",
                        "pattern": "^CY-[0-9]{6}-[A-Z0-9]{4}$",
                        "example": "CY-261201-A3F2",
                    },
                    "fecha_reserva": {"type": "string", "format": "date"},
                    "hora_inicio": {"type": "string", "example": "08:00:00"},
                    "hora_fin": {"type": "string", "example": "10:00:00"},
                    "precio_total": {"type": "string", "example": "120000.00"},
                    "estado_reserva": {
                        "type": "string",
                        "enum": ["Pendiente", "Confirmada", "Cancelada", "Finalizada"],
                    },
                    "estado_pago": {"type": "string", "enum": ["Pendiente", "Pagado"]},
                    "fecha_pago": {"type": ["string", "null"], "format": "date-time"},
                    "observaciones": {"type": "string"},
                    "fecha_creacion": {"type": "string", "format": "date-time"},
                    "cliente": {
                        "type": "object",
                        "properties": {
                            "id_cliente": {"type": "integer"},
                            "nombre": {"type": "string"},
                            "correo": {"type": "string"},
                            "telefono": {"type": "string"},
                        },
                    },
                },
            },
            "PaginaReservas": {
                "type": "object",
                "properties": {
                    "count": {"type": "integer"},
                    "next": {"type": ["string", "null"]},
                    "previous": {"type": ["string", "null"]},
                    "results": {"type": "array", "items": {"$ref": "#/components/schemas/Reserva"}},
                },
            },
            "Dashboard": {
                "type": "object",
                "properties": {
                    "kpis": {
                        "type": "object",
                        "properties": {
                            "reservas_hoy": {"type": "integer"},
                            "pendientes_hoy": {"type": "integer"},
                            "confirmadas_hoy": {"type": "integer"},
                            "canceladas_hoy": {"type": "integer"},
                            "por_aprobar": {"type": "integer"},
                            "ingresos_recibidos": {"type": "string"},
                            "dinero_pendiente": {"type": "string"},
                        },
                    },
                    "serie_actividad": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "fecha": {"type": "string"},
                                "reservas": {"type": "integer"},
                            },
                        },
                    },
                    "serie_ingresos": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "mes": {"type": "string"},
                                "ingresos_recibidos": {"type": "string"},
                            },
                        },
                    },
                    "solicitudes_por_aprobar": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/Reserva"},
                    },
                    "proximos_partidos": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/Reserva"},
                    },
                },
            },
            "ResumenFinanciero": {
                "type": "object",
                "properties": {
                    "periodo": {"type": "string", "enum": ["day", "week", "month", "custom"]},
                    "inicio": {"type": "string", "format": "date"},
                    "fin": {"type": "string", "format": "date"},
                    "ingresos_recibidos": {"type": "string"},
                    "dinero_pendiente": {"type": "string"},
                    "total_reservas": {"type": "integer"},
                    "reservas_pagadas": {"type": "integer"},
                    "reservas_pendientes_pago": {"type": "integer"},
                    "por_dia": {"type": "array", "items": {"type": "object"}},
                    "historial": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/Reserva"},
                    },
                },
            },
        },
    },
}


def _op(resumen, *, auth=True, request=None, respuestas_ok=None, params=None, seguridad=None):
    op: dict = {
        "summary": resumen,
        "responses": {**(_RESPUESTAS_ERROR if auth else {}), **(respuestas_ok or _ok())},
    }
    if auth:
        op["security"] = seguridad or [_BEARER]
    if request:
        op["requestBody"] = {
            "required": True,
            "content": {"application/json": {"schema": request}},
        }
    if params:
        op["parameters"] = params
    return op


def _ok(schema="object", descripcion="OK"):
    return {
        "200": {
            "description": descripcion,
            "content": {"application/json": {"schema": {"$ref": f"#/components/schemas/{schema}"}}},
        }
    }


def _creado(schema):
    return {
        "201": {
            "description": "Creado",
            "content": {"application/json": {"schema": {"$ref": f"#/components/schemas/{schema}"}}},
        }
    }


def _sin_contenido():
    return {"204": {"description": "Eliminado"}}


_REF = lambda nombre: {"$ref": f"#/components/schemas/{nombre}"}  # noqa: E731


SCHEMA["paths"] = {
    "/auth/sync/": {
        "post": _op(
            "Crea o actualiza el perfil tras validar el JWT de Supabase (rol cliente por defecto).",
            auth=False,
            seguridad=[],
            respuestas_ok={
                **_ok("Usuario"),
                "401": _RESPUESTAS_ERROR["401"],
                "403": _RESPUESTAS_ERROR["403"],
                "429": _RESPUESTAS_ERROR["429"],
            },
        )
    },
    "/auth/me/": {
        "get": _op("Perfil del usuario autenticado.", respuestas_ok=_ok("Usuario")),
        "patch": _op(
            "Actualiza nombre o teléfono. Rechaza rol/activo/correo/supabase_uid con 400 campo_no_permitido.",
            request={
                "type": "object",
                "properties": {"nombre": {"type": "string"}, "telefono": {"type": "string"}},
            },
            respuestas_ok=_ok("Usuario"),
        ),
    },
    "/admin/field/": {
        "get": _op("Cancha del administrador autenticado (1:1).", respuestas_ok=_ok("Cancha")),
        "patch": _op(
            "Actualiza los datos de la cancha del administrador.",
            request=_REF("Cancha"),
            respuestas_ok=_ok("Cancha"),
        ),
    },
    "/admin/field/images/": {
        "get": _op(
            "Lista las fotografías de la cancha.",
            respuestas_ok={
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {"schema": {"type": "array", "items": _REF("Imagen")}}
                    },
                }
            },
        ),
        "post": _op(
            "Registra una fotografía (URL subida a Supabase Storage). La primera queda principal.",
            request=_REF("Imagen"),
            respuestas_ok=_creado("Imagen"),
        ),
    },
    "/admin/field/images/{id_imagen}/": {
        "patch": _op(
            "Marca como principal (desmarca la anterior) o actualiza la descripción.",
            request=_REF("Imagen"),
            params=[
                {"name": "id_imagen", "in": "path", "required": True, "schema": {"type": "integer"}}
            ],
            respuestas_ok=_ok("Imagen"),
        ),
        "delete": _op(
            "Elimina la foto; si era principal, promueve la más antigua.",
            params=[
                {"name": "id_imagen", "in": "path", "required": True, "schema": {"type": "integer"}}
            ],
            respuestas_ok=_sin_contenido(),
        ),
    },
    "/admin/field/schedules/": {
        "get": _op(
            "Franjas semanales de atención.",
            respuestas_ok={
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {"schema": {"type": "array", "items": _REF("Horario")}}
                    },
                }
            },
        ),
        "post": _op(
            "Crea una franja. 409 horario_solapado si choca con otra activa del mismo día.",
            request=_REF("Horario"),
            respuestas_ok=_creado("Horario"),
        ),
    },
    "/admin/field/schedules/{id_horario}/": {
        "put": _op(
            "Reemplaza la franja (409 si genera solape).",
            request=_REF("Horario"),
            params=[
                {
                    "name": "id_horario",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "integer"},
                }
            ],
            respuestas_ok=_ok("Horario"),
        ),
        "patch": _op(
            "Actualiza parcialmente la franja.",
            request=_REF("Horario"),
            params=[
                {
                    "name": "id_horario",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "integer"},
                }
            ],
            respuestas_ok=_ok("Horario"),
        ),
        "delete": _op(
            "Elimina la franja.",
            params=[
                {
                    "name": "id_horario",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "integer"},
                }
            ],
            respuestas_ok=_sin_contenido(),
        ),
    },
    "/admin/field/rates/": {
        "get": _op(
            "Tarifas semanales y por fecha especial.",
            respuestas_ok={
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {"schema": {"type": "array", "items": _REF("Tarifa")}}
                    },
                }
            },
        ),
        "post": _op(
            "Crea una tarifa (XOR semanal/especial; 409 tarifa_solapada).",
            request=_REF("Tarifa"),
            respuestas_ok=_creado("Tarifa"),
        ),
    },
    "/admin/field/rates/{id_tarifa}/": {
        "patch": _op(
            "Actualiza la tarifa.",
            request=_REF("Tarifa"),
            params=[
                {"name": "id_tarifa", "in": "path", "required": True, "schema": {"type": "integer"}}
            ],
            respuestas_ok=_ok("Tarifa"),
        ),
        "delete": _op(
            "Elimina la tarifa.",
            params=[
                {"name": "id_tarifa", "in": "path", "required": True, "schema": {"type": "integer"}}
            ],
            respuestas_ok=_sin_contenido(),
        ),
    },
    "/admin/field/rates/preview/": {
        "get": _op(
            "Bloques de 60 min del día con su precio y origen (base/semanal/especial).",
            params=[
                {
                    "name": "fecha",
                    "in": "query",
                    "required": True,
                    "schema": {"type": "string", "format": "date"},
                }
            ],
            respuestas_ok={
                "200": {
                    "description": "Vista previa",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "fecha": {"type": "string"},
                                    "dia_semana": {"type": "integer"},
                                    "precio_base": {"type": "string"},
                                    "bloques": {"type": "array", "items": _REF("BloquePrecio")},
                                },
                            }
                        }
                    },
                }
            },
        )
    },
    "/admin/field/rates/quote/": {
        "get": _op(
            "Precio total de un rango (bloques alineados, dentro de horario).",
            params=[
                {
                    "name": "fecha",
                    "in": "query",
                    "required": True,
                    "schema": {"type": "string", "format": "date"},
                },
                {
                    "name": "inicio",
                    "in": "query",
                    "required": True,
                    "schema": {"type": "string", "example": "08:00"},
                },
                {
                    "name": "fin",
                    "in": "query",
                    "required": True,
                    "schema": {"type": "string", "example": "10:00"},
                },
            ],
            respuestas_ok={
                "200": {
                    "description": "Cotización",
                    "content": {"application/json": {"schema": {"type": "object"}}},
                }
            },
        )
    },
    "/admin/bookings/": {
        "get": _op(
            "Reservas de la cancha, paginadas y filtrables.",
            params=[
                {"name": "fecha", "in": "query", "schema": {"type": "string", "format": "date"}},
                {
                    "name": "estado_reserva",
                    "in": "query",
                    "schema": {
                        "type": "string",
                        "enum": ["Pendiente", "Confirmada", "Cancelada", "Finalizada"],
                    },
                },
                {
                    "name": "estado_pago",
                    "in": "query",
                    "schema": {"type": "string", "enum": ["Pendiente", "Pagado"]},
                },
                {"name": "cliente", "in": "query", "schema": {"type": "string"}},
                {"name": "codigo_reserva", "in": "query", "schema": {"type": "string"}},
                {"name": "page", "in": "query", "schema": {"type": "integer"}},
            ],
            respuestas_ok=_ok("PaginaReservas"),
        )
    },
    "/admin/bookings/{id_reserva}/": {
        "get": _op(
            "Detalle de la reserva con datos de contacto.",
            params=[
                {
                    "name": "id_reserva",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "integer"},
                }
            ],
            respuestas_ok=_ok("Reserva"),
        )
    },
    "/admin/bookings/{id_reserva}/approve/": {
        "post": _op(
            "Pendiente → Confirmada. 409 estado_invalido si el origen no lo permite.",
            params=[
                {
                    "name": "id_reserva",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "integer"},
                }
            ],
            respuestas_ok=_ok("Reserva"),
        )
    },
    "/admin/bookings/{id_reserva}/cancel/": {
        "post": _op(
            "Pendiente|Confirmada → Cancelada (libera el horario).",
            request={
                "type": "object",
                "properties": {"motivo": {"type": "string", "maxLength": 250}},
            },
            params=[
                {
                    "name": "id_reserva",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "integer"},
                }
            ],
            respuestas_ok=_ok("Reserva"),
        )
    },
    "/admin/bookings/{id_reserva}/mark-paid/": {
        "post": _op(
            "Pago presencial: estado_pago=Pagado y fecha_pago=now. 409 si ya estaba pagada.",
            params=[
                {
                    "name": "id_reserva",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "integer"},
                }
            ],
            respuestas_ok=_ok("Reserva"),
        )
    },
    "/admin/finance/dashboard/": {
        "get": _op(
            "KPIs, series, solicitudes por aprobar y próximos partidos.",
            respuestas_ok=_ok("Dashboard"),
        )
    },
    "/admin/finance/summary/": {
        "get": _op(
            "Resumen contable del rango: ingresos recibidos y dinero pendiente.",
            params=[
                {
                    "name": "period",
                    "in": "query",
                    "schema": {
                        "type": "string",
                        "enum": ["day", "week", "month", "custom"],
                        "default": "day",
                    },
                },
                {"name": "start", "in": "query", "schema": {"type": "string", "format": "date"}},
                {"name": "end", "in": "query", "schema": {"type": "string", "format": "date"}},
            ],
            respuestas_ok=_ok("ResumenFinanciero"),
        )
    },
    "/health/": {
        "get": {
            "summary": "Estado del servicio y de la base de datos.",
            "security": [],
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "status": {"type": "string"},
                                    "database": {"type": "boolean"},
                                },
                            }
                        }
                    },
                }
            },
        }
    },
}


def schema_view(request):
    """Sirve el esquema OpenAPI (público; no expone datos)."""
    return JsonResponse(SCHEMA)
