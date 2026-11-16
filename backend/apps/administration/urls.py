from django.urls import path

from .views import AdministrationOverviewView


app_name = "administration"

urlpatterns = [
    path("overview/", AdministrationOverviewView.as_view(), name="overview"),
]
