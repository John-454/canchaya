"""URLs del módulo bookings (§5.3)."""

from django.urls import path

from modules.bookings.api.views import (
    BookingApproveView,
    BookingCancelView,
    BookingDetailView,
    BookingListCreateView,
    BookingMarkPaidView,
)

urlpatterns = [
    path("", BookingListCreateView.as_view(), name="admin-bookings"),
    path("<int:id_reserva>/", BookingDetailView.as_view(), name="admin-booking-detail"),
    path(
        "<int:id_reserva>/approve/",
        BookingApproveView.as_view(),
        name="admin-booking-approve",
    ),
    path(
        "<int:id_reserva>/cancel/",
        BookingCancelView.as_view(),
        name="admin-booking-cancel",
    ),
    path(
        "<int:id_reserva>/mark-paid/",
        BookingMarkPaidView.as_view(),
        name="admin-booking-mark-paid",
    ),
]
