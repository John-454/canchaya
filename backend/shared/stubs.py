"""Stub de endpoint aún no implementado (devuelve 501 con formato de error estándar).

Se devuelve un `HttpResponse` plano a propósito: `APIView.dispatch` es la vía de
DRF que prepara el renderer, y aquí no se usa `dispatch`.
"""

from django.http import JsonResponse

STATUS_501 = 501


def no_implementado(request, *args, **kwargs):
    return JsonResponse(
        {
            "code": "no_implementado",
            "detail": "Se implementa en una iteración posterior.",
        },
        status=STATUS_501,
    )
