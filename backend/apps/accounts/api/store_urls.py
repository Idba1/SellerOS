from django.urls import path

from .store_views import CurrentStoreProfileView

urlpatterns = [
    path("current/", CurrentStoreProfileView.as_view(), name="store-current-profile"),
]
