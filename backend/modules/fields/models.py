"""Models del módulo `fields`.

Decisiones aplicadas:
- R4: todas las horas deben estar en punto (minute=0, second=0) — validado por
  `CheckConstraint` además de en serializers/servicios.
- R2: los solapes se impiden con `ExclusionConstraint` de PostgreSQL sobre un
  rango semiabierto `[inicio, fin)` construido con la función SQL `canchaya_timerange`
  (ver migración 0003). No hay `timerange` nativo en PostgreSQL.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.contrib.postgres.constraints import ExclusionConstraint
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q, UniqueConstraint

# ---------------------------------------------------------------------------
# Expresiones SQL reutilizables (PostgreSQL)
# ---------------------------------------------------------------------------
TIMERANGE_FN = "canchaya_timerange"


class TimeRange(models.Func):
    """Rango semiabierto [start, end) sobre columnas TIME, en minutos.

    PostgreSQL no tiene un tipo `timerange`; se emula devolviendo un
    `int4range` de segundos desde medianoche, que sí admite operador `&&`
    y por tanto `EXCLUDE USING gist`.
    """

    function = TIMERANGE_FN

    def __init__(self, start: str, end: str, **extra):
        self.start_field = start
        self.end_field = end
        super().__init__(models.F(start), models.F(end), **extra)

    def as_sql(self, compiler, connection):
        return f"{self.function}({self.start_field}, {self.end_field})", []


def aligned_hour_check(field: str, name: str) -> models.CheckConstraint:
    """R4: la hora debe ser múltiplo exacto de 60 minutos (minuto y segundo 0)."""
    return models.CheckConstraint(
        condition=Q(**{f"{field}__minute": 0, f"{field}__second": 0}),
        name=name,
    )


# ---------------------------------------------------------------------------
# Cancha (1:1 con administrador)
# ---------------------------------------------------------------------------
class Cancha(models.Model):
    id_cancha = models.BigAutoField(primary_key=True)
    id_administrador = models.OneToOneField(
        "users_auth.Usuario",
        on_delete=models.PROTECT,
        related_name="cancha",
        db_column="id_administrador",
    )
    nombre = models.CharField(max_length=150)
    direccion = models.CharField(max_length=250)
    zona = models.CharField(max_length=100, null=True, blank=True)
    descripcion = models.TextField(blank=True, default="")
    precio_base = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    estado = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "canchas"
        verbose_name = "cancha"
        verbose_name_plural = "canchas"
        constraints = [
            models.CheckConstraint(
                condition=Q(precio_base__gte=0), name="ck_canchas_precio_base_no_negativo"
            ),
            models.CheckConstraint(
                condition=Q(nombre__regex=r".*\S.*"), name="ck_canchas_nombre_no_vacio"
            ),
        ]
        indexes = [
            models.Index(fields=["estado"], name="ix_canchas_estado"),
            models.Index(fields=["zona"], name="ix_canchas_zona"),
        ]

    def __str__(self) -> str:
        return self.nombre


# ---------------------------------------------------------------------------
# Imágenes (máximo una principal por cancha)
# ---------------------------------------------------------------------------
class ImagenCancha(models.Model):
    id_imagen = models.BigAutoField(primary_key=True)
    id_cancha = models.ForeignKey(
        Cancha, on_delete=models.CASCADE, related_name="imagenes", db_column="id_cancha"
    )
    url_imagen = models.TextField()
    descripcion = models.CharField(max_length=250, blank=True, default="")
    imagen_principal = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "imagenes_cancha"
        verbose_name = "imagen de cancha"
        verbose_name_plural = "imágenes de cancha"
        constraints = [
            # Máximo una imagen principal por cancha (índice único parcial).
            UniqueConstraint(
                fields=["id_cancha"],
                condition=Q(imagen_principal=True),
                name="uq_imagen_principal_por_cancha",
            ),
            models.CheckConstraint(
                condition=Q(url_imagen__regex=r"^https?://"),
                name="ck_imagenes_url_http",
            ),
        ]
        ordering = ["-imagen_principal", "fecha_creacion"]
        indexes = [models.Index(fields=["id_cancha"], name="ix_imagenes_cancha")]

    def __str__(self) -> str:
        return f"Imagen {self.pk} de {self.id_cancha_id}"


# ---------------------------------------------------------------------------
# Horarios de operación
# ---------------------------------------------------------------------------
class HorarioOperacion(models.Model):
    LUNES, DOMINGO = 1, 7

    id_horario = models.BigAutoField(primary_key=True)
    id_cancha = models.ForeignKey(
        Cancha, on_delete=models.CASCADE, related_name="horarios", db_column="id_cancha"
    )
    dia_semana = models.SmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(7)])
    hora_apertura = models.TimeField()
    hora_cierre = models.TimeField()
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "horarios_operacion"
        verbose_name = "horario de operación"
        verbose_name_plural = "horarios de operación"
        ordering = ["dia_semana", "hora_apertura"]
        constraints = [
            models.CheckConstraint(
                condition=Q(dia_semana__gte=1) & Q(dia_semana__lte=7),
                name="ck_horarios_dia_semana_1_7",
            ),
            models.CheckConstraint(
                condition=Q(hora_apertura__lt=models.F("hora_cierre")),
                name="ck_horarios_rango_positivo",
            ),
            aligned_hour_check("hora_apertura", "ck_horarios_apertura_en_punto"),
            aligned_hour_check("hora_cierre", "ck_horarios_cierre_en_punto"),
            # R2: sin solapes entre franjas activas del mismo día.
            ExclusionConstraint(
                name="ex_horarios_no_solape",
                expressions=[
                    ("id_cancha", "="),
                    ("dia_semana", "="),
                    (TimeRange("hora_apertura", "hora_cierre"), "&&"),
                ],
                condition=Q(activo=True),
            ),
        ]
        indexes = [
            models.Index(fields=["id_cancha", "dia_semana"], name="ix_horarios_cancha_dia"),
        ]

    def __str__(self) -> str:
        return (
            f"{self.get_dia_semana_display()} {self.hora_apertura:%H:%M}-{self.hora_cierre:%H:%M}"
        )


# ---------------------------------------------------------------------------
# Tarifas (semanal XOR fecha especial)
# ---------------------------------------------------------------------------
class Tarifa(models.Model):
    id_tarifa = models.BigAutoField(primary_key=True)
    id_cancha = models.ForeignKey(
        Cancha, on_delete=models.CASCADE, related_name="tarifas", db_column="id_cancha"
    )
    dia_semana = models.SmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(7)]
    )
    fecha_especial = models.DateField(null=True, blank=True)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    precio_hora = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "tarifas"
        verbose_name = "tarifa"
        verbose_name_plural = "tarifas"
        ordering = ["-fecha_especial", "dia_semana", "hora_inicio"]
        constraints = [
            # Semanal XOR especial.
            models.CheckConstraint(
                condition=(Q(dia_semana__isnull=False) & Q(fecha_especial__isnull=True))
                | (Q(dia_semana__isnull=True) & Q(fecha_especial__isnull=False)),
                name="ck_tarifas_semanal_xor_especial",
            ),
            models.CheckConstraint(
                condition=Q(dia_semana__isnull=True)
                | (Q(dia_semana__gte=1) & Q(dia_semana__lte=7)),
                name="ck_tarifas_dia_semana_1_7",
            ),
            models.CheckConstraint(
                condition=Q(hora_inicio__lt=models.F("hora_fin")),
                name="ck_tarifas_rango_positivo",
            ),
            aligned_hour_check("hora_inicio", "ck_tarifas_inicio_en_punto"),
            aligned_hour_check("hora_fin", "ck_tarifas_fin_en_punto"),
            models.CheckConstraint(
                condition=Q(precio_hora__gt=0), name="ck_tarifas_precio_positivo"
            ),
            # Sin solapes entre tarifas semanales activas del mismo día.
            ExclusionConstraint(
                name="ex_tarifas_semanal_no_solape",
                expressions=[
                    ("id_cancha", "="),
                    ("dia_semana", "="),
                    (TimeRange("hora_inicio", "hora_fin"), "&&"),
                ],
                condition=Q(dia_semana__isnull=False, activo=True),
            ),
            # Sin solapes entre tarifas especiales activas de la misma fecha.
            ExclusionConstraint(
                name="ex_tarifas_especial_no_solape",
                expressions=[
                    ("id_cancha", "="),
                    ("fecha_especial", "="),
                    (TimeRange("hora_inicio", "hora_fin"), "&&"),
                ],
                condition=Q(fecha_especial__isnull=False, activo=True),
            ),
        ]
        indexes = [
            models.Index(fields=["id_cancha", "dia_semana"], name="ix_tarifas_cancha_dia"),
            models.Index(fields=["id_cancha", "fecha_especial"], name="ix_tarifas_cancha_fecha"),
        ]

    def __str__(self) -> str:
        ref = f"día {self.dia_semana}" if self.dia_semana else str(self.fecha_especial)
        return f"{ref} {self.hora_inicio:%H:%M}-{self.hora_fin:%H:%M} @ {self.precio_hora}"

    @property
    def es_especial(self) -> bool:
        return self.fecha_especial is not None

    def aplica_a(self, fecha: dt.date, hora: dt.time) -> bool:
        """¿Esta tarifa cubre el bloque que empieza en `hora` del día `fecha`?"""
        if not (self.hora_inicio <= hora < self.hora_fin):
            return False
        if self.fecha_especial is not None:
            return self.fecha_especial == fecha
        return self.dia_semana == fecha.isoweekday()
