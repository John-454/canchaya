"""URLs del módulo finance (§5.4)."""

from django.urls import path

from modules.finance.api.views import DashboardView, SummaryView

urlpatterns = [
    path("dashboard/", DashboardView.as_view(), name="admin-finance-dashboard"),
    path("summary/", SummaryView.as_view(), name="admin-finance-summary"),
]
