# Généré par Django 5.2.19 le 14 novembre 2026

import django.db.models.deletion
import django.db.models.functions.text
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Departement",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("nom", models.CharField(max_length=150)),
                ("description", models.TextField(blank=True)),
                ("est_actif", models.BooleanField(default=True)),
                ("cree_le", models.DateTimeField(auto_now_add=True)),
                ("modifie_le", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "departements",
                "ordering": ("nom",),
                "constraints": [
                    models.UniqueConstraint(
                        django.db.models.functions.text.Lower("nom"),
                        name="departements_nom_unique_sans_casse",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="Poste",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("nom", models.CharField(max_length=150)),
                ("description", models.TextField(blank=True)),
                ("est_actif", models.BooleanField(default=True)),
                ("cree_le", models.DateTimeField(auto_now_add=True)),
                ("modifie_le", models.DateTimeField(auto_now=True)),
                (
                    "departement",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="postes",
                        to="organisation.departement",
                    ),
                ),
            ],
            options={
                "db_table": "postes",
                "ordering": ("departement__nom", "nom"),
                "constraints": [
                    models.UniqueConstraint(
                        models.F("departement"),
                        django.db.models.functions.text.Lower("nom"),
                        name="postes_departement_nom_unique_sans_casse",
                    )
                ],
            },
        ),
    ]
