from django.urls import path

from .views import AssistantDraftView


urlpatterns = [
    path("drafts/", AssistantDraftView.as_view(), name="assistant-draft"),
]
