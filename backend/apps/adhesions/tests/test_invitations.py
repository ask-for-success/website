from datetime import timedelta

from django.contrib.auth.models import Group, Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.organisation.models import Departement, Poste

from ..models import EtatIntegration, EtatInvitationAdhesion, InvitationAdhesion
from ..operations import accepter_invitation_adhesion, creer_invitation_adhesion


class DonneesInvitationMixin:
    @classmethod
    def creer_donnees_communes(cls):
        cls.responsable = User.objects.create_user(
            email="responsable-rh@example.com",
            first_name="Responsable",
            last_name="Ressources humaines",
            phone_number="+212600000401",
            password="MotDePasseSolide!2026",
        )
        cls.responsable.groups.add(Group.objects.get(name="content_manager"))
        cls.responsable.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="accounts",
                codename="manage_hr",
            )
        )
        cls.utilisateur_non_autorise = User.objects.create_user(
            email="sans-autorisation@example.com",
            first_name="Sans",
            last_name="Autorisation",
            phone_number="+212600000402",
            password="MotDePasseSolide!2026",
        )
        cls.departement = Departement.objects.create(nom="Communication")
        cls.poste = Poste.objects.create(
            departement=cls.departement,
            nom="Responsable des medias",
        )

    def donnees_creation(self, **modifications):
        donnees = {
            "adresse_electronique": "membre-invite@example.com",
            "prenom": "Membre",
            "nom": "Invite",
            "departement": self.departement,
            "poste": self.poste,
            "responsable": self.responsable,
        }
        donnees.update(modifications)
        return donnees


class OperationsInvitationAdhesionTests(DonneesInvitationMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.creer_donnees_communes()

    def test_creation_prepare_compte_adhesion_affectation_et_integration(self):
        resultat = creer_invitation_adhesion(**self.donnees_creation())

        utilisateur = resultat.invitation.utilisateur
        self.assertFalse(utilisateur.is_active)
        self.assertIsNone(utilisateur.phone_number)
        self.assertFalse(utilisateur.has_usable_password())
        self.assertEqual(resultat.invitation.adhesion.utilisateur, utilisateur)
        self.assertEqual(
            resultat.invitation.adhesion.integration.etat,
            EtatIntegration.A_FAIRE,
        )
        affectation = resultat.invitation.adhesion.affectations.get()
        self.assertEqual(affectation.departement, self.departement)
        self.assertEqual(affectation.poste, self.poste)

    def test_jeton_brut_n_est_jamais_stocke(self):
        resultat = creer_invitation_adhesion(**self.donnees_creation())

        self.assertNotEqual(
            resultat.invitation.empreinte_jeton,
            resultat.jeton,
        )
        self.assertEqual(len(resultat.invitation.empreinte_jeton), 64)
        duree = resultat.invitation.expire_le - timezone.now()
        self.assertGreater(duree, timedelta(hours=47, minutes=59))
        self.assertLessEqual(duree, timedelta(hours=48))

    def test_acceptation_active_compte_et_consomme_jeton(self):
        resultat = creer_invitation_adhesion(**self.donnees_creation())

        utilisateur = accepter_invitation_adhesion(
            jeton=resultat.jeton,
            numero_telephone="+212600000403",
            mot_de_passe="NouveauMotDePasse!2026",
        )

        utilisateur.refresh_from_db()
        resultat.invitation.refresh_from_db()
        self.assertTrue(utilisateur.is_active)
        self.assertEqual(utilisateur.phone_number, "+212600000403")
        self.assertTrue(utilisateur.check_password("NouveauMotDePasse!2026"))
        self.assertEqual(
            resultat.invitation.etat,
            EtatInvitationAdhesion.UTILISEE,
        )
        self.assertIsNotNone(resultat.invitation.utilisee_le)
        with self.assertRaises(ValidationError):
            accepter_invitation_adhesion(
                jeton=resultat.jeton,
                numero_telephone="+212600000404",
                mot_de_passe="AutreMotDePasse!2026",
            )

    def test_nouvelle_invitation_annule_ancienne(self):
        premiere = creer_invitation_adhesion(**self.donnees_creation())
        seconde = creer_invitation_adhesion(**self.donnees_creation())

        premiere.invitation.refresh_from_db()
        self.assertEqual(
            premiere.invitation.etat,
            EtatInvitationAdhesion.ANNULEE,
        )
        self.assertIsNotNone(premiere.invitation.annulee_le)
        self.assertEqual(
            premiere.invitation.adhesion_id,
            seconde.invitation.adhesion_id,
        )
        self.assertNotEqual(premiere.jeton, seconde.jeton)
        self.assertEqual(
            InvitationAdhesion.objects.filter(
                utilisateur=seconde.invitation.utilisateur,
                etat=EtatInvitationAdhesion.ACTIVE,
            ).count(),
            1,
        )

    def test_invitation_expiree_est_marquee_et_refusee(self):
        resultat = creer_invitation_adhesion(**self.donnees_creation())
        resultat.invitation.expire_le = timezone.now() - timedelta(seconds=1)
        resultat.invitation.save(update_fields=("expire_le", "modifiee_le"))

        with self.assertRaises(ValidationError):
            accepter_invitation_adhesion(
                jeton=resultat.jeton,
                numero_telephone="+212600000403",
                mot_de_passe="NouveauMotDePasse!2026",
            )

        resultat.invitation.refresh_from_db()
        self.assertEqual(
            resultat.invitation.etat,
            EtatInvitationAdhesion.EXPIREE,
        )

    def test_creation_exige_autorisation_ressources_humaines(self):
        with self.assertRaises(PermissionDenied):
            creer_invitation_adhesion(
                **self.donnees_creation(
                    responsable=self.utilisateur_non_autorise
                )
            )

    def test_compte_actif_existant_utilise_un_autre_parcours(self):
        User.objects.create_user(
            email="membre-invite@example.com",
            first_name="Compte",
            last_name="Existant",
            phone_number="+212600000405",
            password="MotDePasseSolide!2026",
        )

        with self.assertRaises(ValidationError):
            creer_invitation_adhesion(**self.donnees_creation())


class ApiInvitationAdhesionTests(DonneesInvitationMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.creer_donnees_communes()

    def corps_creation(self):
        return {
            "adresse_electronique": "api-invite@example.com",
            "prenom": "Membre",
            "nom": "Invite",
            "departement_id": str(self.departement.id),
            "poste_id": str(self.poste.id),
        }

    def test_api_creation_et_configuration_du_compte(self):
        self.client.force_authenticate(self.responsable)
        creation = self.client.post(
            "/api/v1/adhesions/invitations/",
            self.corps_creation(),
            format="json",
        )

        self.assertEqual(creation.status_code, status.HTTP_201_CREATED)
        self.assertIn("jeton_configuration", creation.data)

        self.client.force_authenticate(user=None)
        acceptation = self.client.post(
            "/api/v1/adhesions/invitations/accepter/",
            {
                "jeton": creation.data["jeton_configuration"],
                "numero_telephone": "+212600000406",
                "mot_de_passe": "NouveauMotDePasse!2026",
                "confirmation_mot_de_passe": "NouveauMotDePasse!2026",
            },
            format="json",
        )
        self.assertEqual(acceptation.status_code, status.HTTP_204_NO_CONTENT)

        connexion = self.client.post(
            "/api/v1/auth/login/",
            {
                "email": "api-invite@example.com",
                "password": "NouveauMotDePasse!2026",
            },
            format="json",
        )
        self.assertEqual(connexion.status_code, status.HTTP_200_OK)

    def test_api_creation_refuse_utilisateur_non_autorise(self):
        self.client.force_authenticate(self.utilisateur_non_autorise)

        reponse = self.client.post(
            "/api/v1/adhesions/invitations/",
            self.corps_creation(),
            format="json",
        )

        self.assertEqual(reponse.status_code, status.HTTP_403_FORBIDDEN)

    def test_schema_documente_champs_francais(self):
        reponse = self.client.get("/api/schema/")

        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        chemin = reponse.data["paths"]["/api/v1/adhesions/invitations/"]["post"]
        reference = chemin["requestBody"]["content"]["application/json"][
            "schema"
        ]["$ref"]
        nom_composant = reference.rsplit("/", 1)[-1]
        schema = reponse.data["components"]["schemas"][nom_composant]
        self.assertTrue(
            {
                "adresse_electronique",
                "prenom",
                "nom",
                "departement_id",
                "poste_id",
            }.issubset(set(schema["required"]))
        )
