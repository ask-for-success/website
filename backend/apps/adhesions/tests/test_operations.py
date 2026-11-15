from django.contrib.auth.models import Group, Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase

from apps.accounts.models import User
from apps.adhesions.models import EtatIntegration
from apps.adhesions.operations import changer_affectation, creer_adhesion_initiale
from apps.organisation.models import Departement, Poste


class OperationsAdhesionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.membre = User.objects.create_user(
            email="candidat@example.com",
            first_name="Candidat",
            last_name="Accepté",
            phone_number="+212600000301",
            password="StrongPassword!2026",
        )
        cls.responsable = User.objects.create_user(
            email="rh@example.com",
            first_name="Responsable",
            last_name="Autorisé",
            phone_number="+212600000302",
            password="StrongPassword!2026",
        )
        cls.responsable.groups.add(Group.objects.get(name="content_manager"))
        cls.responsable.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="accounts",
                codename="manage_hr",
            )
        )
        cls.utilisateur_non_autorise = User.objects.create_user(
            email="non-autorise@example.com",
            first_name="Utilisateur",
            last_name="Ordinaire",
            phone_number="+212600000303",
            password="StrongPassword!2026",
        )
        cls.departement_initial = Departement.objects.create(nom="Technologie")
        cls.poste_initial = Poste.objects.create(
            departement=cls.departement_initial,
            nom="Développeur",
        )
        cls.nouveau_departement = Departement.objects.create(nom="Marketing")
        cls.nouveau_poste = Poste.objects.create(
            departement=cls.nouveau_departement,
            nom="Responsable marketing",
        )

    def creer_adhesion(self):
        return creer_adhesion_initiale(
            utilisateur=self.membre,
            departement=self.departement_initial,
            poste=self.poste_initial,
            responsable=self.responsable,
        )

    def test_creation_initiale_cree_integration_et_affectation(self):
        adhesion = self.creer_adhesion()

        self.assertEqual(adhesion.integration.etat, EtatIntegration.A_FAIRE)
        affectation = adhesion.affectations.get()
        self.assertEqual(affectation.departement, self.departement_initial)
        self.assertEqual(affectation.poste, self.poste_initial)
        self.assertEqual(affectation.attribuee_par, self.responsable)

    def test_creation_initiale_exige_permission_ressources_humaines(self):
        with self.assertRaises(PermissionDenied):
            creer_adhesion_initiale(
                utilisateur=self.membre,
                departement=self.departement_initial,
                poste=self.poste_initial,
                responsable=self.utilisateur_non_autorise,
            )

    def test_changement_ferme_ancienne_affectation_et_cree_nouvelle(self):
        adhesion = self.creer_adhesion()
        integration_id = adhesion.integration.id

        nouvelle_affectation = changer_affectation(
            adhesion=adhesion,
            nouveau_departement=self.nouveau_departement,
            nouveau_poste=self.nouveau_poste,
            responsable=self.responsable,
            motif="Acceptation de la candidature au département marketing",
        )

        ancienne_affectation = adhesion.affectations.exclude(
            id=nouvelle_affectation.id
        ).get()
        self.assertIsNotNone(ancienne_affectation.date_fin)
        self.assertEqual(
            ancienne_affectation.motif_fin,
            "Acceptation de la candidature au département marketing",
        )
        self.assertEqual(nouvelle_affectation.departement, self.nouveau_departement)
        self.assertEqual(nouvelle_affectation.poste, self.nouveau_poste)
        adhesion.integration.refresh_from_db()
        self.assertEqual(adhesion.integration.id, integration_id)
        self.assertEqual(adhesion.affectations.filter(date_fin__isnull=True).count(), 1)

    def test_changement_exige_un_motif(self):
        adhesion = self.creer_adhesion()

        with self.assertRaises(ValidationError):
            changer_affectation(
                adhesion=adhesion,
                nouveau_departement=self.nouveau_departement,
                nouveau_poste=self.nouveau_poste,
                responsable=self.responsable,
                motif="   ",
            )

    def test_changement_exige_permission_ressources_humaines(self):
        adhesion = self.creer_adhesion()

        with self.assertRaises(PermissionDenied):
            changer_affectation(
                adhesion=adhesion,
                nouveau_departement=self.nouveau_departement,
                nouveau_poste=self.nouveau_poste,
                responsable=self.utilisateur_non_autorise,
                motif="Changement non autorisé",
            )

    def test_changement_refuse_poste_d_un_autre_departement(self):
        adhesion = self.creer_adhesion()

        with self.assertRaises(ValidationError):
            changer_affectation(
                adhesion=adhesion,
                nouveau_departement=self.nouveau_departement,
                nouveau_poste=self.poste_initial,
                responsable=self.responsable,
                motif="Poste incohérent",
            )
