from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serialiseurs import (
    AcceptationInvitationAdhesionSerialiseur,
    CreationInvitationAdhesionSerialiseur,
    ResultatInvitationAdhesionSerialiseur,
)


class CreationInvitationAdhesionVue(APIView):
    @extend_schema(
        tags=["Adhesions"],
        summary="Inviter un membre deja accepte",
        description=(
            "Cree un compte inactif, son adhesion, son affectation initiale et un "
            "jeton de configuration valable 48 heures. Cette operation exige un "
            "gestionnaire de contenu autorise a gerer les ressources humaines. "
            "Le jeton brut est retourne une seule fois pour permettre les essais "
            "tant que l'envoi de courriels n'est pas encore branche."
        ),
        request=CreationInvitationAdhesionSerialiseur,
        responses={
            201: ResultatInvitationAdhesionSerialiseur,
            400: OpenApiResponse(description="Donnees invalides."),
            401: OpenApiResponse(description="Authentification obligatoire."),
            403: OpenApiResponse(description="Autorisation RH obligatoire."),
        },
    )
    def post(self, request):
        serialiseur = CreationInvitationAdhesionSerialiseur(
            data=request.data,
            context={"request": request},
        )
        serialiseur.is_valid(raise_exception=True)
        resultat = serialiseur.save()
        reponse = {
            "invitation_id": resultat.invitation.id,
            "adresse_electronique": resultat.invitation.utilisateur.email,
            "expire_le": resultat.invitation.expire_le,
            "jeton_configuration": resultat.jeton,
        }
        return Response(
            ResultatInvitationAdhesionSerialiseur(reponse).data,
            status=status.HTTP_201_CREATED,
        )


class AcceptationInvitationAdhesionVue(APIView):
    permission_classes = (permissions.AllowAny,)

    @extend_schema(
        tags=["Adhesions"],
        summary="Configurer un compte invite",
        description=(
            "Utilise une seule fois le jeton d'invitation pour enregistrer le "
            "numero de telephone et le mot de passe, puis active le compte. "
            "Cette action ne decide pas l'acceptation du candidat : l'adhesion "
            "a deja ete approuvee avant la creation de l'invitation."
        ),
        request=AcceptationInvitationAdhesionSerialiseur,
        responses={
            204: None,
            400: OpenApiResponse(description="Invitation ou donnees invalides."),
        },
    )
    def post(self, request):
        serialiseur = AcceptationInvitationAdhesionSerialiseur(data=request.data)
        serialiseur.is_valid(raise_exception=True)
        serialiseur.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
