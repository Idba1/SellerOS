from django.urls import path

from .views import ProfitSummaryView


urlpatterns = [
    path("summary/", ProfitSummaryView.as_view(), name="profit-summary"),
]
