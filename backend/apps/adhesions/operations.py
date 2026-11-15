import hashlib
import secrets
from dataclasses import dataclass
from datetime import timedelta

from django.contrib.auth import password_validation
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.organisation.models import Departement, Poste

from .models import (
    Adhesion,
    AffectationMembre,
    EtatInvitationAdhesion,
    IntegrationMembre,
    InvitationAdhesion,
)


DUREE_VALIDITE_INVITATION = timedelta(hours=48)


@dataclass(frozen=True)
class ResultatCreationInvitation:
    invitation: InvitationAdhesion
    jeton: str


def _calculer_empreinte_jeton(jeton: str) -> str:
    return hashlib.sha256(jeton.encode("utf-8")).hexdigest()


def verifier_responsable_ressources_humaines(responsable) -> None:
    if responsable.is_superuser:
        return

    est_gestionnaire_contenu = responsable.groups.filter(
        name="content_manager"
    ).exists()
    possede_permission = responsable.has_perm("accounts.manage_hr")
    if not est_gestionnaire_contenu or not possede_permission:
        raise PermissionDenied(
            "Cette opération exige la gestion du contenu et la permission des ressources humaines."
        )


def verifier_poste_departement(poste: Poste, departement: Departement) -> None:
    if poste.departement_id != departement.id:
        raise ValidationError(
            {"poste": "Le poste doit appartenir au département sélectionné."}
        )


@transaction.atomic
def creer_adhesion_initiale(
    *,
    utilisateur,
    departement: Departement,
    poste: Poste,
    responsable,
) -> Adhesion:
    verifier_responsable_ressources_humaines(responsable)
    verifier_poste_departement(poste, departement)

    if Adhesion.objects.filter(utilisateur=utilisateur).exists():
        raise ValidationError(
            {"utilisateur": "Cet utilisateur possède déjà une adhésion."}
        )

    adhesion = Adhesion.objects.create(utilisateur=utilisateur)
    IntegrationMembre.objects.create(adhesion=adhesion)
    affectation = AffectationMembre(
        adhesion=adhesion,
        departement=departement,
        poste=poste,
        attribuee_par=responsable,
    )
    affectation.full_clean()
    affectation.save()
    return adhesion


@transaction.atomic
def changer_affectation(
    *,
    adhesion: Adhesion,
    nouveau_departement: Departement,
    nouveau_poste: Poste,
    responsable,
    motif: str,
) -> AffectationMembre:
    verifier_responsable_ressources_humaines(responsable)
    verifier_poste_departement(nouveau_poste, nouveau_departement)

    motif = motif.strip()
    if not motif:
        raise ValidationError({"motif": "Le motif du changement est obligatoire."})

    adhesion_verrouillee = Adhesion.objects.select_for_update().get(pk=adhesion.pk)
    try:
        affectation_actuelle = AffectationMembre.objects.select_for_update().get(
            adhesion=adhesion_verrouillee,
            date_fin__isnull=True,
        )
    except AffectationMembre.DoesNotExist as erreur:
        raise ValidationError(
            {"adhesion": "Aucune affectation active ne peut être remplacée."}
        ) from erreur

    if (
        affectation_actuelle.departement_id == nouveau_departement.id
        and affectation_actuelle.poste_id == nouveau_poste.id
    ):
        raise ValidationError(
            {"affectation": "La nouvelle affectation doit être différente."}
        )

    instant = timezone.now()
    affectation_actuelle.date_fin = instant
    affectation_actuelle.motif_fin = motif
    affectation_actuelle.save(
        update_fields=("date_fin", "motif_fin", "modifie_le")
    )

    nouvelle_affectation = AffectationMembre(
        adhesion=adhesion_verrouillee,
        departement=nouveau_departement,
        poste=nouveau_poste,
        attribuee_par=responsable,
        date_debut=instant,
    )
    nouvelle_affectation.full_clean()
    nouvelle_affectation.save()
    return nouvelle_affectation


@transaction.atomic
def creer_invitation_adhesion(
    *,
    adresse_electronique: str,
    prenom: str,
    nom: str,
    departement: Departement,
    poste: Poste,
    responsable,
) -> ResultatCreationInvitation:
    verifier_responsable_ressources_humaines(responsable)
    verifier_poste_departement(poste, departement)

    adresse_electronique = User.objects.normalize_email(
        adresse_electronique
    ).lower()
    prenom = prenom.strip()
    nom = nom.strip()
    erreurs = {}
    if not adresse_electronique:
        erreurs["adresse_electronique"] = "L'adresse electronique est obligatoire."
    if not prenom:
        erreurs["prenom"] = "Le prenom est obligatoire."
    if not nom:
        erreurs["nom"] = "Le nom est obligatoire."
    if erreurs:
        raise ValidationError(erreurs)

    utilisateur = (
        User.objects.select_for_update()
        .filter(email__iexact=adresse_electronique)
        .first()
    )
    if utilisateur is None:
        utilisateur = User.objects.create_user(
            email=adresse_electronique,
            password=None,
            first_name=prenom,
            last_name=nom,
            phone_number=None,
            is_active=False,
        )
        adhesion = creer_adhesion_initiale(
            utilisateur=utilisateur,
            departement=departement,
            poste=poste,
            responsable=responsable,
        )
    else:
        if utilisateur.is_active:
            raise ValidationError(
                {
                    "adresse_electronique": (
                        "Ce compte existe deja. Utiliser le parcours d'admission "
                        "d'un compte existant."
                    )
                }
            )
        if utilisateur.has_usable_password() or not InvitationAdhesion.objects.filter(
            utilisateur=utilisateur
        ).exists():
            raise ValidationError(
                {
                    "adresse_electronique": (
                        "Ce compte inactif ne provient pas d'une invitation d'adhesion."
                    )
                }
            )

        try:
            adhesion = Adhesion.objects.select_for_update().get(
                utilisateur=utilisateur
            )
            affectation = AffectationMembre.objects.get(
                adhesion=adhesion,
                date_fin__isnull=True,
            )
        except (Adhesion.DoesNotExist, AffectationMembre.DoesNotExist) as erreur:
            raise ValidationError(
                {
                    "adresse_electronique": (
                        "Le compte invite ne possede pas une adhesion complete."
                    )
                }
            ) from erreur

        if (
            affectation.departement_id != departement.id
            or affectation.poste_id != poste.id
        ):
            raise ValidationError(
                {
                    "poste": (
                        "Une nouvelle invitation doit conserver l'affectation initiale."
                    )
                }
            )

        utilisateur.first_name = prenom
        utilisateur.last_name = nom
        utilisateur.full_clean()
        utilisateur.save(update_fields=("first_name", "last_name", "updated_at"))

    instant = timezone.now()
    InvitationAdhesion.objects.filter(
        utilisateur=utilisateur,
        etat=EtatInvitationAdhesion.ACTIVE,
    ).update(
        etat=EtatInvitationAdhesion.ANNULEE,
        annulee_le=instant,
        modifiee_le=instant,
    )

    jeton = secrets.token_urlsafe(32)
    invitation = InvitationAdhesion(
        adhesion=adhesion,
        utilisateur=utilisateur,
        creee_par=responsable,
        empreinte_jeton=_calculer_empreinte_jeton(jeton),
        expire_le=instant + DUREE_VALIDITE_INVITATION,
    )
    invitation.full_clean()
    invitation.save()
    return ResultatCreationInvitation(invitation=invitation, jeton=jeton)


def accepter_invitation_adhesion(
    *,
    jeton: str,
    numero_telephone: str,
    mot_de_passe: str,
) -> User:
    erreur_apres_validation = None
    utilisateur = None

    with transaction.atomic():
        try:
            invitation = InvitationAdhesion.objects.select_for_update().get(
                empreinte_jeton=_calculer_empreinte_jeton(jeton)
            )
        except InvitationAdhesion.DoesNotExist as erreur:
            raise ValidationError(
                {"jeton": "Cette invitation est invalide ou n'est plus utilisable."}
            ) from erreur

        if invitation.etat != EtatInvitationAdhesion.ACTIVE:
            raise ValidationError(
                {"jeton": "Cette invitation est invalide ou n'est plus utilisable."}
            )

        instant = timezone.now()
        if invitation.expire_le <= instant:
            invitation.etat = EtatInvitationAdhesion.EXPIREE
            invitation.save(update_fields=("etat", "modifiee_le"))
            erreur_apres_validation = ValidationError(
                {"jeton": "Cette invitation a expire."}
            )
        else:
            utilisateur = User.objects.select_for_update().get(
                pk=invitation.utilisateur_id
            )
            numero_telephone = numero_telephone.strip()
            if not numero_telephone:
                raise ValidationError(
                    {"numero_telephone": "Le numero de telephone est obligatoire."}
                )
            if User.objects.filter(phone_number=numero_telephone).exclude(
                pk=utilisateur.pk
            ).exists():
                raise ValidationError(
                    {
                        "numero_telephone": (
                            "Ce numero de telephone est deja utilise."
                        )
                    }
                )

            try:
                password_validation.validate_password(
                    mot_de_passe,
                    user=utilisateur,
                )
            except ValidationError as erreur:
                raise ValidationError(
                    {"mot_de_passe": list(erreur.messages)}
                ) from erreur
            utilisateur.phone_number = numero_telephone
            utilisateur.is_active = True
            utilisateur.set_password(mot_de_passe)
            utilisateur.full_clean()
            utilisateur.save(
                update_fields=(
                    "phone_number",
                    "is_active",
                    "password",
                    "updated_at",
                )
            )

            invitation.etat = EtatInvitationAdhesion.UTILISEE
            invitation.utilisee_le = instant
            invitation.save(
                update_fields=("etat", "utilisee_le", "modifiee_le")
            )

    if erreur_apres_validation:
        raise erreur_apres_validation
    return utilisateur
