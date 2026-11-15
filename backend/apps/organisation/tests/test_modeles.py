import uuid

from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase

from apps.organisation.models import Departement, Poste


class ModelesOrganisationTests(TestCase):
    def setUp(self):
        self.departement = Departement.objects.create(
            nom="Technologie",
            description="Département de la technologie",
        )

    def test_departement_utilise_un_identifiant_unique_universel(self):
        self.assertIsInstance(self.departement.id, uuid.UUID)

    def test_nom_departement_est_unique_sans_tenir_compte_de_la_casse(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Departement.objects.create(nom="TECHNOLOGIE")

    def test_poste_appartient_a_un_seul_departement(self):
        poste = Poste.objects.create(
            departement=self.departement,
            nom="Développeur",
        )

        self.assertEqual(poste.departement, self.departement)
        self.assertQuerySetEqual(self.departement.postes.all(), [poste])

    def test_nom_poste_est_unique_dans_un_departement_sans_casse(self):
        Poste.objects.create(
            departement=self.departement,
            nom="Développeur",
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            Poste.objects.create(
                departement=self.departement,
                nom="DÉVELOPPEUR",
            )

    def test_meme_nom_poste_est_autorise_dans_deux_departements(self):
        autre_departement = Departement.objects.create(nom="Marketing")
        premier_poste = Poste.objects.create(
            departement=self.departement,
            nom="Responsable",
        )
        second_poste = Poste.objects.create(
            departement=autre_departement,
            nom="Responsable",
        )

        self.assertNotEqual(premier_poste.departement, second_poste.departement)

    def test_suppression_departement_avec_poste_est_protegee(self):
        Poste.objects.create(
            departement=self.departement,
            nom="Développeur",
        )

        with self.assertRaises(ProtectedError):
            self.departement.delete()

    def test_departement_et_poste_peuvent_etre_desactives(self):
        poste = Poste.objects.create(
            departement=self.departement,
            nom="Développeur",
        )
        self.departement.est_actif = False
        self.departement.save(update_fields=("est_actif", "modifie_le"))
        poste.est_actif = False
        poste.save(update_fields=("est_actif", "modifie_le"))

        self.departement.refresh_from_db()
        poste.refresh_from_db()
        self.assertFalse(self.departement.est_actif)
        self.assertFalse(poste.est_actif)
