"""Alta controlada de administradores (Opción A de la Iteración 2).

Uso típico:
  1. Crear el usuario en Supabase → Authentication → Users (email/password o Google).
  2. Copiar su UUID (columna *User UID*).
  3. Ejecutar:

        python manage.py aprovisionar_admin --correo admin@cancha.com \
            --uid 3f2c...  --nombre "Juan Pérez" --telefono 3001234567

Si el perfil ya existe por correo (p. ej. el seed de desarrollo), solo se
actualizan rol y `supabase_uid`. Si ya existía como cliente, se promueve.
"""

from __future__ import annotations

import uuid

from django.core.management.base import BaseCommand, CommandError
from shared.exceptions import DomainError

from modules.users_auth import services
from modules.users_auth.models import Rol


class Command(BaseCommand):
    help = "Vincula un usuario de Supabase Auth como administrador de una cancha."

    def add_arguments(self, parser):
        parser.add_argument("--correo", required=True, help="Correo del administrador")
        parser.add_argument("--uid", required=False, help="User UID de Supabase Auth")
        parser.add_argument("--nombre", required=False, help="Nombre visible")
        parser.add_argument("--telefono", required=False, help="Celular colombiano")
        parser.add_argument(
            "--cancha",
            required=False,
            help="Nombre comercial de la cancha (se crea si el admin no tiene una).",
        )
        parser.add_argument(
            "--direccion", required=False, default="", help="Dirección de la cancha"
        )

    def handle(self, *args, **options):
        try:
            usuario = services.aprovisionar_admin(
                correo=options["correo"],
                supabase_uid=options.get("uid"),
                nombre=options.get("nombre"),
                telefono=options.get("telefono"),
            )
        except DomainError as exc:
            raise CommandError(f"[{exc.code}] {exc.detail}") from exc
        except (ValueError, uuid.JSONDecodeError) as exc:  # pragma: no cover - defensivo
            raise CommandError(f"UUID inválido: {exc}") from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"Administrador listo: {usuario.correo} "
                f"(rol={usuario.rol}, uid={usuario.supabase_uid})"
            )
        )

        if usuario.rol != Rol.ADMINISTRADOR:  # pragma: no cover - defensivo
            raise CommandError("El usuario no quedó como administrador.")

        from modules.fields.services import get_cancha_by_admin

        cancha = get_cancha_by_admin(usuario)
        if cancha is None:
            if not options.get("cancha"):
                self.stdout.write(
                    self.style.WARNING(
                        'Sin cancha asignada. Añade --cancha "Nombre" --direccion "..." '
                        "para crearla ahora."
                    )
                )
                return
            from modules.fields.models import Cancha

            cancha = Cancha.objects.create(
                id_administrador=usuario,
                nombre=options["cancha"],
                direccion=options.get("direccion") or "",
            )
            self.stdout.write(self.style.SUCCESS(f"Cancha creada: {cancha.nombre}"))
        else:
            self.stdout.write(f"Cancha actual: {cancha.nombre} (id={cancha.pk})")
