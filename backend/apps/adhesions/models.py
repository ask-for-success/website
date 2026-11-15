import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.organisation.models import Departement, Poste


class EtatAdhesion(models.TextChoices):
    EN_ATTENTE_INTEGRATION = "en_attente_integration", "En attente d'intégration"
    ACTIVE = "active", "Active"
    INACTIVE = "inactive", "Inactive"


class EtatIntegration(models.TextChoices):
    A_FAIRE = "a_faire", "À faire"
    EN_COURS = "en_cours", "En cours"
    TERMINEE = "terminee", "Terminée"


class EtatInvitationAdhesion(models.TextChoices):
    ACTIVE = "active", "Active"
    UTILISEE = "utilisee", "Utilisee"
    EXPIREE = "expiree", "Expiree"
    ANNULEE = "annulee", "Annulee"


class Adhesion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    utilisateur = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="adhesion",
    )
    etat = models.CharField(
        max_length=32,
        choices=EtatAdhesion.choices,
        default=EtatAdhesion.EN_ATTENTE_INTEGRATION,
    )
    acceptee_le = models.DateTimeField(default=timezone.now)
    cree_le = models.DateTimeField(auto_now_add=True)
    modifie_le = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "adhesions"
        ordering = ("-acceptee_le",)

    def __str__(self) -> str:
        return f"Adhésion de {self.utilisateur.email}"


    @property
    def user(self):
        return self.utilisateur

    @user.setter
    def user(self, value):
        self.utilisateur = value

    @property
    def user_id(self):
        return self.utilisateur_id

    @property
    def status(self):
        return self.etat

    @status.setter
    def status(self, value):
        self.etat = value


Membership = Adhesion
MembershipStatus = EtatAdhesion


class IntegrationMembre(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    adhesion = models.OneToOneField(
        Adhesion,
        on_delete=models.CASCADE,
        related_name="integration",
    )
    etat = models.CharField(
        max_length=16,
        choices=EtatIntegration.choices,
        default=EtatIntegration.A_FAIRE,
    )
    commencee_le = models.DateTimeField(null=True, blank=True)
    terminee_le = models.DateTimeField(null=True, blank=True)
    cree_le = models.DateTimeField(auto_now_add=True)
    modifie_le = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "integrations_membres"

    def __str__(self) -> str:
        return f"Intégration de {self.adhesion.utilisateur.email}"


class InvitationAdhesion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    adhesion = models.ForeignKey(
        Adhesion,
        on_delete=models.PROTECT,
        related_name="invitations",
    )
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="invitations_adhesion",
    )
    creee_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="invitations_adhesion_creees",
    )
    empreinte_jeton = models.CharField(max_length=64, unique=True, editable=False)
    etat = models.CharField(
        max_length=16,
        choices=EtatInvitationAdhesion.choices,
        default=EtatInvitationAdhesion.ACTIVE,
    )
    expire_le = models.DateTimeField()
    utilisee_le = models.DateTimeField(null=True, blank=True)
    annulee_le = models.DateTimeField(null=True, blank=True)
    creee_le = models.DateTimeField(auto_now_add=True)
    modifiee_le = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "invitations_adhesion"
        ordering = ("-creee_le",)
        constraints = (
            models.UniqueConstraint(
                fields=("utilisateur",),
                condition=models.Q(etat=EtatInvitationAdhesion.ACTIVE),
                name="invitation_une_active_par_utilisateur",
            ),
        )

    def clean(self) -> None:
        super().clean()
        if (
            self.adhesion_id
            and self.utilisateur_id
            and self.adhesion.utilisateur_id != self.utilisateur_id
        ):
            raise ValidationError(
                {
                    "utilisateur": (
                        "L'utilisateur de l'invitation doit etre celui de l'adhesion."
                    )
                }
            )

    def __str__(self) -> str:
        return f"Invitation d'adhesion de {self.utilisateur.email}"


class AffectationMembre(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    adhesion = models.ForeignKey(
        Adhesion,
        on_delete=models.PROTECT,
        related_name="affectations",
    )
    departement = models.ForeignKey(
        Departement,
        on_delete=models.PROTECT,
        related_name="affectations_membres",
    )
    poste = models.ForeignKey(
        Poste,
        on_delete=models.PROTECT,
        related_name="affectations_membres",
    )
    attribuee_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="affectations_attribuees",
    )
    date_debut = models.DateTimeField(default=timezone.now)
    date_fin = models.DateTimeField(null=True, blank=True)
    motif_fin = models.TextField(blank=True)
    cree_le = models.DateTimeField(auto_now_add=True)
    modifie_le = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "affectations_membres"
        ordering = ("-date_debut",)
        constraints = (
            models.UniqueConstraint(
                fields=("adhesion",),
                condition=models.Q(date_fin__isnull=True),
                name="affectations_une_active_par_adhesion",
            ),
        )

    def clean(self) -> None:
        super().clean()
        if (
            self.poste_id
            and self.departement_id
            and self.poste.departement_id != self.departement_id
        ):
            raise ValidationError(
                {"poste": "Le poste doit appartenir au département sélectionné."}
            )
        if self.date_fin and self.date_fin <= self.date_debut:
            raise ValidationError(
                {"date_fin": "La date de fin doit être postérieure à la date de début."}
            )

    def __str__(self) -> str:
        return (
            f"{self.adhesion.utilisateur.email} — "
            f"{self.departement.nom} — {self.poste.nom}"
        )
