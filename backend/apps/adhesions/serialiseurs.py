from django.core.exceptions import ValidationError as ErreurValidationDjango
from rest_framework import serializers

from apps.organisation.models import Departement, Poste

from .operations import accepter_invitation_adhesion, creer_invitation_adhesion


def convertir_erreur_validation(erreur: ErreurValidationDjango):
    if hasattr(erreur, "message_dict"):
        return erreur.message_dict
    return {"erreurs_generales": list(erreur.messages)}


class CreationInvitationAdhesionSerialiseur(serializers.Serializer):
    adresse_electronique = serializers.EmailField()
    prenom = serializers.CharField(max_length=150)
    nom = serializers.CharField(max_length=150)
    departement_id = serializers.PrimaryKeyRelatedField(
        queryset=Departement.objects.filter(est_actif=True),
        source="departement",
    )
    poste_id = serializers.PrimaryKeyRelatedField(
        queryset=Poste.objects.filter(est_actif=True),
        source="poste",
    )

    def create(self, donnees_validees):
        try:
            return creer_invitation_adhesion(
                responsable=self.context["request"].user,
                **donnees_validees,
            )
        except ErreurValidationDjango as erreur:
            raise serializers.ValidationError(
                convertir_erreur_validation(erreur)
            ) from erreur


class ResultatInvitationAdhesionSerialiseur(serializers.Serializer):
    invitation_id = serializers.UUIDField()
    adresse_electronique = serializers.EmailField()
    expire_le = serializers.DateTimeField()
    jeton_configuration = serializers.CharField()


class AcceptationInvitationAdhesionSerialiseur(serializers.Serializer):
    jeton = serializers.CharField(trim_whitespace=False)
    numero_telephone = serializers.CharField(max_length=32)
    mot_de_passe = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )
    confirmation_mot_de_passe = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    def validate(self, donnees):
        if donnees["mot_de_passe"] != donnees["confirmation_mot_de_passe"]:
            raise serializers.ValidationError(
                {
                    "confirmation_mot_de_passe": (
                        "Les mots de passe doivent etre identiques."
                    )
                }
            )
        return donnees

    def create(self, donnees_validees):
        donnees_validees.pop("confirmation_mot_de_passe")
        try:
            return accepter_invitation_adhesion(**donnees_validees)
        except ErreurValidationDjango as erreur:
            raise serializers.ValidationError(
                convertir_erreur_validation(erreur)
            ) from erreur
