"""Seed idempotente de demo (T1.12): 1 administrador + 1 cancha + horarios + tarifas."""

from __future__ import annotations

import datetime as dt
import uuid
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from modules.fields.models import Cancha, HorarioOperacion, ImagenCancha, Tarifa
from modules.users_auth.models import Rol, Usuario

ADMIN_UID = uuid.UUID("00000000-0000-4000-8000-000000000001")
ADMIN_EMAIL = "propietario@canchaya.test"


class Command(BaseCommand):
    help = "Crea un administrador con su cancha, horarios (L-V 08-12 y 13-22) y tarifas demo."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Recrea horarios y tarifas.")

    @transaction.atomic
    def handle(self, *args, **options):
        admin, _ = Usuario.objects.get_or_create(
            supabase_uid=ADMIN_UID,
            defaults={
                "nombre": "Propietario Demo",
                "correo": ADMIN_EMAIL,
                "telefono": "3001234567",
                "rol": Rol.ADMINISTRADOR,
            },
        )
        cancha, _ = Cancha.objects.get_or_create(
            id_administrador=admin,
            defaults={
                "nombre": "Cancha La Jugada",
                "direccion": "Calle 45 # 12-30",
                "zona": "Chapinero",
                "descripcion": "Cancha sintética 7v7 con iluminación nocturna.",
                "precio_base": Decimal("60000.00"),
                "estado": True,
            },
        )

        if options["reset"]:
            cancha.horarios.all().delete()
            cancha.tarifas.all().delete()

        for dia in range(1, 6):
            for abre, cierra in (("08:00", "12:00"), ("13:00", "22:00")):
                HorarioOperacion.objects.get_or_create(
                    id_cancha=cancha,
                    dia_semana=dia,
                    hora_apertura=dt.time.fromisoformat(abre),
                    hora_cierre=dt.time.fromisoformat(cierra),
                    defaults={"activo": True},
                )
        Tarifa.objects.get_or_create(
            id_cancha=cancha,
            dia_semana=6,
            hora_inicio=dt.time(8),
            hora_fin=dt.time(12),
            defaults={"precio_hora": Decimal("70000.00"), "activo": True},
        )
        Tarifa.objects.get_or_create(
            id_cancha=cancha,
            fecha_especial=dt.date(dt.date.today().year, 12, 24),
            hora_inicio=dt.time(13),
            hora_fin=dt.time(22),
            defaults={"precio_hora": Decimal("95000.00"), "activo": True},
        )
        ImagenCancha.objects.get_or_create(
            id_cancha=cancha,
            url_imagen="https://placehold.co/1200x800/15803d/ffffff?text=canchaya",
            defaults={"descripcion": "Vista general", "imagen_principal": True},
        )

        self.stdout.write(self.style.SUCCESS(f"Cancha lista: {cancha} (admin {admin.correo})"))
