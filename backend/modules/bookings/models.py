"""Models del módulo `bookings`.

Decisiones aplicadas:
- R4: `hora_inicio`/`hora_fin` en punto y duración múltiplo de 60 (≥60), en BD y servicio.
- R5: `codigo_reserva` `CY-YYMMDD-XXXX` con UNIQUE; el generador con reintento vive
  en `bookings/services.py` (Iteración 4).
- R3: el solape se impide con `ExclusionConstraint` parcial para los estados que
  bloquean horario (Pendiente, Confirmada).
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.postgres.constraints import ExclusionConstraint
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from modules.fields.models import Cancha, TimeRange, aligned_hour_check


class EstadoReserva(models.TextChoices):
    PENDIENTE = "Pendiente", "Pendiente"
    CONFIRMADA = "Confirmada", "Confirmada"
    CANCELADA = "Cancelada", "Cancelada"
    FINALIZADA = "Finalizada", "Finalizada"


class EstadoPago(models.TextChoices):
    PENDIENTE = "Pendiente", "Pendiente"
    PAGADO = "Pagado", "Pagado"


# Estados que ocupan el horario.
ESTADOS_BLOQUEANTES = [EstadoReserva.PENDIENTE, EstadoReserva.CONFIRMADA]


class Reserva(models.Model):
    id_reserva = models.BigAutoField(primary_key=True)
    codigo_reserva = models.CharField(max_length=30, unique=True)
    id_cancha = models.ForeignKey(
        Cancha, on_delete=models.PROTECT, related_name="reservas", db_column="id_cancha"
    )
    id_cliente = models.ForeignKey(
        "users_auth.Usuario",
        on_delete=models.RESTRICT,
        related_name="reservas",
        db_column="id_cliente",
    )

    # Snapshot de contacto al momento de crear la reserva (no se recalcula).
    nombre_cliente = models.CharField(max_length=120)
    correo_cliente = models.EmailField(max_length=150)
    telefono_cliente = models.CharField(max_length=30)

    fecha_reserva = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    precio_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    estado_reserva = models.CharField(
        max_length=20, choices=EstadoReserva.choices, default=EstadoReserva.PENDIENTE
    )
    estado_pago = models.CharField(
        max_length=20, choices=EstadoPago.choices, default=EstadoPago.PENDIENTE
    )
    fecha_pago = models.DateTimeField(null=True, blank=True)
    observaciones = models.TextField(blank=True, default="")
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "reservas"
        verbose_name = "reserva"
        verbose_name_plural = "reservas"
        ordering = ["-fecha_reserva", "-hora_inicio"]
        constraints = [
            models.CheckConstraint(
                condition=Q(estado_reserva__in=[c for c in EstadoReserva.values]),
                name="ck_reservas_estado_valido",
            ),
            models.CheckConstraint(
                condition=Q(estado_pago__in=[c for c in EstadoPago.values]),
                name="ck_reservas_estado_pago_valido",
            ),
            # Coherencia pago <-> fecha_pago.
            models.CheckConstraint(
                condition=(Q(estado_pago="Pagado") & Q(fecha_pago__isnull=False))
                | (Q(estado_pago="Pendiente") & Q(fecha_pago__isnull=True)),
                name="ck_reservas_pago_fecha_coherente",
            ),
            models.CheckConstraint(
                condition=Q(hora_inicio__lt=models.F("hora_fin")),
                name="ck_reservas_rango_positivo",
            ),
            aligned_hour_check("hora_inicio", "ck_reservas_inicio_en_punto"),
            aligned_hour_check("hora_fin", "ck_reservas_fin_en_punto"),
            models.CheckConstraint(
                condition=Q(precio_total__gte=0), name="ck_reservas_precio_no_negativo"
            ),
            models.CheckConstraint(
                condition=Q(codigo_reserva__regex=r"^CY-[0-9]{6}-[A-Z0-9]{4}$"),
                name="ck_reservas_codigo_formato",
            ),
            # R3: ningún solape para reservas que ocupan horario.
            ExclusionConstraint(
                name="ex_reservas_no_solape",
                expressions=[
                    ("id_cancha", "="),
                    ("fecha_reserva", "="),
                    (TimeRange("hora_inicio", "hora_fin"), "&&"),
                ],
                condition=Q(estado_reserva__in=ESTADOS_BLOQUEANTES),
            ),
        ]
        indexes = [
            models.Index(fields=["id_cancha", "fecha_reserva"], name="ix_reservas_cancha_fecha"),
            models.Index(
                fields=["estado_reserva", "fecha_reserva", "hora_fin"],
                name="ix_reservas_expira",
            ),
            models.Index(fields=["id_cliente"], name="ix_reservas_cliente"),
            models.Index(fields=["estado_pago"], name="ix_reservas_estado_pago"),
        ]

    def __str__(self) -> str:
        return f"{self.codigo_reserva} ({self.fecha_reserva} {self.hora_inicio:%H:%M})"

    @property
    def bloquea_horario(self) -> bool:
        return self.estado_reserva in ESTADOS_BLOQUEANTES
