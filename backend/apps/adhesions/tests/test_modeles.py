from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.adhesions.models import (
    Adhesion,
    AffectationMembre,
    EtatAdhesion,
    EtatIntegration,
    IntegrationMembre,
)
from apps.organisation.models import Departement, Poste


class ModelesAdhesionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.utilisateur = User.objects.create_user(
            email="membre@example.com",
            first_name="Membre",
            last_name="Test",
            phone_number="+212600000201",
            password="StrongPassword!2026",
        )
        cls.responsable = User.objects.create_user(
            email="responsable@example.com",
            first_name="Responsable",
            last_name="RH",
            phone_number="+212600000202",
            password="StrongPassword!2026",
        )
        cls.departement = Departement.objects.create(nom="Technologie")
        cls.poste = Poste.objects.create(
            departement=cls.departement,
            nom="Développeur",
        )

    def creer_adhesion(self):
        return Adhesion.objects.create(utilisateur=self.utilisateur)

    def test_une_seule_adhesion_par_utilisateur(self):
        self.creer_adhesion()

        with self.assertRaises(IntegrityError), transaction.atomic():
            self.creer_adhesion()

    def test_adhesion_commence_en_attente_integration(self):
        adhesion = self.creer_adhesion()

        self.assertEqual(adhesion.etat, EtatAdhesion.EN_ATTENTE_INTEGRATION)

    def test_une_seule_integration_par_adhesion(self):
        adhesion = self.creer_adhesion()
        IntegrationMembre.objects.create(adhesion=adhesion)

        with self.assertRaises(IntegrityError), transaction.atomic():
            IntegrationMembre.objects.create(adhesion=adhesion)

    def test_integration_commence_a_faire(self):
        integration = IntegrationMembre.objects.create(
            adhesion=self.creer_adhesion()
        )

        self.assertEqual(integration.etat, EtatIntegration.A_FAIRE)

    def test_une_seule_affectation_active_par_adhesion(self):
        adhesion = self.creer_adhesion()
        AffectationMembre.objects.create(
            adhesion=adhesion,
            departement=self.departement,
            poste=self.poste,
            attribuee_par=self.responsable,
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            AffectationMembre.objects.create(
                adhesion=adhesion,
                departement=self.departement,
                poste=self.poste,
                attribuee_par=self.responsable,
            )

    def test_nouvelle_affectation_possible_apres_cloture(self):
        adhesion = self.creer_adhesion()
        ancienne_affectation = AffectationMembre.objects.create(
            adhesion=adhesion,
            departement=self.departement,
            poste=self.poste,
            attribuee_par=self.responsable,
        )
        ancienne_affectation.date_fin = timezone.now()
        ancienne_affectation.motif_fin = "Changement de département"
        ancienne_affectation.save(update_fields=("date_fin", "motif_fin", "modifie_le"))
        nouveau_departement = Departement.objects.create(nom="Marketing")
        nouveau_poste = Poste.objects.create(
            departement=nouveau_departement,
            nom="Responsable marketing",
        )

        nouvelle_affectation = AffectationMembre.objects.create(
            adhesion=adhesion,
            departement=nouveau_departement,
            poste=nouveau_poste,
            attribuee_par=self.responsable,
        )

        self.assertIsNone(nouvelle_affectation.date_fin)
        self.assertEqual(adhesion.affectations.count(), 2)

    def test_poste_doit_appartenir_au_departement(self):
        adhesion = self.creer_adhesion()
        autre_departement = Departement.objects.create(nom="Marketing")
        affectation = AffectationMembre(
            adhesion=adhesion,
            departement=autre_departement,
            poste=self.poste,
            attribuee_par=self.responsable,
        )

        with self.assertRaises(ValidationError):
            affectation.full_clean()

    def test_date_fin_doit_suivre_date_debut(self):
        adhesion = self.creer_adhesion()
        maintenant = timezone.now()
        affectation = AffectationMembre(
            adhesion=adhesion,
            departement=self.departement,
            poste=self.poste,
            attribuee_par=self.responsable,
            date_debut=maintenant,
            date_fin=maintenant - timedelta(days=1),
        )

        with self.assertRaises(ValidationError):
            affectation.full_clean()
