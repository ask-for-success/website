import uuid

from django.db import models
from django.db.models.functions import Lower


class Departement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    est_actif = models.BooleanField(default=True)
    cree_le = models.DateTimeField(auto_now_add=True)
    modifie_le = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "departements"
        ordering = ("nom",)
        constraints = (
            models.UniqueConstraint(
                Lower("nom"),
                name="departements_nom_unique_sans_casse",
            ),
        )

    def clean(self) -> None:
        super().clean()
        self.nom = self.nom.strip()

    def __str__(self) -> str:
        return self.nom


class Poste(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    departement = models.ForeignKey(
        Departement,
        on_delete=models.PROTECT,
        related_name="postes",
    )
    nom = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    est_actif = models.BooleanField(default=True)
    cree_le = models.DateTimeField(auto_now_add=True)
    modifie_le = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "postes"
        ordering = ("departement__nom", "nom")
        constraints = (
            models.UniqueConstraint(
                models.F("departement"),
                Lower("nom"),
                name="postes_departement_nom_unique_sans_casse",
            ),
        )

    def clean(self) -> None:
        super().clean()
        self.nom = self.nom.strip()

    def __str__(self) -> str:
        return f"{self.departement.nom} — {self.nom}"
