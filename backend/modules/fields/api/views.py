"""Vistas del panel de administrador: Mi cancha, fotos, horarios y tarifas (§5.2).

**Protección común:** todas heredan de `MiCanchaAPIView`, que declara
`IsFieldAdmin`. Ese permiso:

- responde `401` si no hay token (lo emite `SupabaseJWTAuthentication`);
- responde `403 rol_requerido` si el usuario autenticado no es administrador;
- responde `403 admin_sin_cancha` si es administrador pero no tiene cancha;
- deja la cancha del admin en `request.cancha` (1:1), de modo que las vistas
  **no reciben ni aceptan** un `id_cancha`.
"""

from __future__ import annotations

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from shared.exceptions import NotFoundError
from shared.permissions import IsFieldAdmin

from modules.fields import services
from modules.fields.api.serializers import (
    CanchaSerializer,
    HorarioSerializer,
    ImagenSerializer,
    ImagenUpdateSerializer,
    PreviewQuerySerializer,
    TarifaSerializer,
)
from modules.fields.services_pricing import calcular_precio, tarifar_fecha


class MiCanchaAPIView(APIView):
    """Base de todo el panel: solo el administrador dueño de su cancha."""

    permission_classes = [IsFieldAdmin]

    @property
    def cancha(self):
        return self.request.cancha


class MiCanchaView(MiCanchaAPIView):
    """GET / PATCH /api/v1/admin/field/ (T3.4)."""

    def get(self, request):
        return Response(CanchaSerializer(self.cancha).data)

    def patch(self, request):
        serializer = CanchaSerializer(self.cancha, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        cancha = services.update_mi_cancha(self.cancha, serializer.validated_data)
        return Response(CanchaSerializer(cancha).data)


class ImagenListCreateView(MiCanchaAPIView):
    """GET / POST /api/v1/admin/field/images/ (T3.5)."""

    def get(self, request):
        return Response(ImagenSerializer(services.list_images(self.cancha), many=True).data)

    def post(self, request):
        serializer = ImagenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        datos = serializer.validated_data
        imagen = services.add_image(
            self.cancha,
            url_imagen=datos["url_imagen"],
            descripcion=datos.get("descripcion", ""),
            principal=datos.get("imagen_principal", False),
        )
        return Response(ImagenSerializer(imagen).data, status=status.HTTP_201_CREATED)


class ImagenDetailView(MiCanchaAPIView):
    """PATCH / DELETE /api/v1/admin/field/images/{id_imagen}/ (T3.5)."""

    def patch(self, request, id_imagen: int):
        serializer = ImagenUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        if serializer.validated_data.get("imagen_principal"):
            imagen = services.set_imagen_principal(self.cancha, id_imagen)
        else:
            imagen = services.get_imagen(self.cancha, id_imagen)
            if "descripcion" in serializer.validated_data:
                imagen.descripcion = serializer.validated_data["descripcion"]
                imagen.save(update_fields=["descripcion"])
        return Response(ImagenSerializer(imagen).data)

    def delete(self, request, id_imagen: int):
        services.delete_image(self.cancha, id_imagen)
        return Response(status=status.HTTP_204_NO_CONTENT)


class HorarioListCreateView(MiCanchaAPIView):
    """GET / POST /api/v1/admin/field/schedules/ (T3.6)."""

    def get(self, request):
        return Response(HorarioSerializer(services.list_schedules(self.cancha), many=True).data)

    def post(self, request):
        serializer = HorarioSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        horario = services.add_schedule(self.cancha, serializer.validated_data)
        return Response(HorarioSerializer(horario).data, status=status.HTTP_201_CREATED)


class HorarioDetailView(MiCanchaAPIView):
    """PUT / PATCH / DELETE /api/v1/admin/field/schedules/{id_horario}/."""

    def put(self, request, id_horario: int):
        return self._actualizar(request, id_horario, partial=False)

    def patch(self, request, id_horario: int):
        return self._actualizar(request, id_horario, partial=True)

    def _actualizar(self, request, id_horario: int, *, partial: bool):
        horario = self.cancha.horarios.filter(pk=id_horario).first()
        if horario is None:
            raise NotFoundError("El horario no existe en tu cancha.")
        serializer = HorarioSerializer(horario, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        horario = services.update_schedule(self.cancha, id_horario, serializer.validated_data)
        return Response(HorarioSerializer(horario).data)

    def delete(self, request, id_horario: int):
        services.delete_schedule(self.cancha, id_horario)
        return Response(status=status.HTTP_204_NO_CONTENT)


class TarifaListCreateView(MiCanchaAPIView):
    """GET / POST /api/v1/admin/field/rates/ (T3.7)."""

    def get(self, request):
        return Response(TarifaSerializer(services.list_rates(self.cancha), many=True).data)

    def post(self, request):
        serializer = TarifaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tarifa = services.add_rate(self.cancha, serializer.validated_data)
        return Response(TarifaSerializer(tarifa).data, status=status.HTTP_201_CREATED)


class TarifaDetailView(MiCanchaAPIView):
    """PATCH / DELETE /api/v1/admin/field/rates/{id_tarifa}/."""

    def patch(self, request, id_tarifa: int):
        tarifa_actual = self.cancha.tarifas.filter(pk=id_tarifa).first()
        if tarifa_actual is None:
            raise NotFoundError("La tarifa no existe en tu cancha.")
        serializer = TarifaSerializer(tarifa_actual, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        tarifa = services.update_rate(self.cancha, id_tarifa, serializer.validated_data)
        return Response(TarifaSerializer(tarifa).data)

    def delete(self, request, id_tarifa: int):
        services.delete_rate(self.cancha, id_tarifa)
        return Response(status=status.HTTP_204_NO_CONTENT)


class TarifasPreviewView(MiCanchaAPIView):
    """GET /api/v1/admin/field/rates/preview/?fecha=YYYY-MM-DD (T3.8).

    Devuelve los bloques de 60 min del día con el precio que aplica a cada uno
    y el origen (`base` | `semanal` | `especial`).
    """

    def get(self, request):
        params = PreviewQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        fecha = params.validated_data["fecha"]
        bloques = tarifar_fecha(self.cancha, fecha)
        return Response(
            {
                "fecha": fecha.isoformat(),
                "dia_semana": fecha.isoweekday(),
                "precio_base": str(self.cancha.precio_base),
                "bloques": [
                    {
                        "hora_inicio": b.hora_inicio.strftime("%H:%M"),
                        "hora_fin": b.hora_fin.strftime("%H:%M"),
                        "precio": str(b.precio),
                        "origen": b.origen,
                    }
                    for b in bloques
                ],
            }
        )


class PrecioRangoView(MiCanchaAPIView):
    """GET /api/v1/admin/field/rates/quote/?fecha=..&inicio=HH:00&fin=HH:00.

    Apoyo a la Iteración 4 (crear reservas) y herramienta de verificación del
    `PricingEngine` desde el panel.
    """

    def get(self, request):
        from datetime import date, time

        try:
            fecha = date.fromisoformat(request.query_params.get("fecha", ""))
            inicio = time.fromisoformat(request.query_params.get("inicio", ""))
            fin = time.fromisoformat(request.query_params.get("fin", ""))
        except ValueError as exc:
            return Response(
                {"code": "parametros_invalidos", "detail": f"Parámetros inválidos: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        total, bloques = calcular_precio(self.cancha, fecha, inicio, fin)
        return Response(
            {
                "fecha": fecha.isoformat(),
                "hora_inicio": inicio.strftime("%H:%M"),
                "hora_fin": fin.strftime("%H:%M"),
                "precio_total": str(total),
                "bloques": [
                    {
                        "hora_inicio": b.hora_inicio.strftime("%H:%M"),
                        "hora_fin": b.hora_fin.strftime("%H:%M"),
                        "precio": str(b.precio),
                        "origen": b.origen,
                    }
                    for b in bloques
                ],
            }
        )
