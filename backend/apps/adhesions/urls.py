from django.urls import path

from .vues import AcceptationInvitationAdhesionVue, CreationInvitationAdhesionVue


app_name = "adhesions"

urlpatterns = [
    path(
        "invitations/",
        CreationInvitationAdhesionVue.as_view(),
        name="creer_invitation",
    ),
    path(
        "invitations/accepter/",
        AcceptationInvitationAdhesionVue.as_view(),
        name="accepter_invitation",
    ),
]
