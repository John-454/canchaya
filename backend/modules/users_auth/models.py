"""Models del módulo `users_auth`.

Frontera: ningún otro módulo puede importar `Usuario` desde aquí; deben usar
`users_auth.services` (Iteración 2).
"""

from __future__ import annotations

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.db.models import Q


class Rol(models.TextChoices):
    CLIENTE = "cliente", "Cliente"
    ADMINISTRADOR = "administrador", "Administrador"


class Usuario(AbstractBaseUser, PermissionsMixin):
    """Perfil de usuario sincronizado con Supabase Auth.

    Decisión R1: `telefono` es NULL en BD para no bloquear el primer login con
    Google Sign-In; la obligatoriedad se valida en el servicio antes de reservar.

    `PermissionsMixin` se hereda solo por compatibilidad de API, pero sus campos
    (`groups`, `user_permissions`) se anulan: las cuentas de administrador se
    aprovisionan de forma controlada y la autorización es por `rol`, no por
    permisos de Django. Así se evita la dependencia circular con `auth`/`admin`.
    """

    id_usuario = models.BigAutoField(primary_key=True)

    groups = None
    user_permissions = None

    supabase_uid = models.UUIDField(unique=True)
    nombre = models.CharField(max_length=120)
    correo = models.EmailField(max_length=150, unique=True)
    telefono = models.CharField(max_length=30, null=True, blank=True)
    rol = models.CharField(max_length=20, choices=Rol.choices, default=Rol.CLIENTE)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    USERNAME_FIELD = "correo"
    EMAIL_FIELD = "correo"
    REQUIRED_FIELDS = ["nombre"]

    class Meta:
        db_table = "usuarios"
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        constraints = [
            models.CheckConstraint(
                condition=Q(rol__in=["cliente", "administrador"]),
                name="ck_usuarios_rol_valido",
            ),
            models.CheckConstraint(
                condition=Q(nombre__regex=r".*\S.*"),
                name="ck_usuarios_nombre_no_vacio",
            ),
        ]
        indexes = [
            models.Index(fields=["rol", "activo"], name="ix_usuarios_rol_activo"),
        ]

    def __str__(self) -> str:
        return f"{self.nombre} <{self.correo}>"

    # --- Contrato mínimo esperado por Django / DRF -------------------------
    @property
    def is_active(self) -> bool:  # usado por Django admin
        return self.activo

    @property
    def is_anonymous(self) -> bool:
        return False

    @property
    def is_authenticated(self) -> bool:
        return True

    def has_perm(self, perm, obj=None) -> bool:
        return self.rol == Rol.ADMINISTRADOR and self.is_superuser

    def has_module_perms(self, app_label) -> bool:
        return self.is_superuser

    @property
    def requiere_telefono(self) -> bool:
        """R1: se solicita antes de confirmar la primera reserva."""
        return not (self.telefono or "").strip()
