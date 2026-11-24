from django.urls import path

from .views import ExpenseDetailView, ExpenseListView

urlpatterns = [
    path("", ExpenseListView.as_view(), name="expense-list"),
    path("<uuid:expense_id>/", ExpenseDetailView.as_view(), name="expense-detail"),
]
