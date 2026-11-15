# Généré par Django 5.2.19 le 14 novembre 2026

import django.db.models.deletion
import django.utils.timezone
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("accounts", "0003_hr_as_content_manager_permission"),
        ("organisation", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Adhesion",
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
                (
                    "etat",
                    models.CharField(
                        choices=[
                            ("en_attente_integration", "En attente d'intégration"),
                            ("active", "Active"),
                            ("inactive", "Inactive"),
                        ],
                        default="en_attente_integration",
                        max_length=32,
                    ),
                ),
                ("acceptee_le", models.DateTimeField(default=django.utils.timezone.now)),
                ("cree_le", models.DateTimeField(auto_now_add=True)),
                ("modifie_le", models.DateTimeField(auto_now=True)),
                (
                    "utilisateur",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="adhesion",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "adhesions",
                "ordering": ("-acceptee_le",),
            },
        ),
        migrations.CreateModel(
            name="IntegrationMembre",
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
                (
                    "etat",
                    models.CharField(
                        choices=[
                            ("a_faire", "À faire"),
                            ("en_cours", "En cours"),
                            ("terminee", "Terminée"),
                        ],
                        default="a_faire",
                        max_length=16,
                    ),
                ),
                ("commencee_le", models.DateTimeField(blank=True, null=True)),
                ("terminee_le", models.DateTimeField(blank=True, null=True)),
                ("cree_le", models.DateTimeField(auto_now_add=True)),
                ("modifie_le", models.DateTimeField(auto_now=True)),
                (
                    "adhesion",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="integration",
                        to="adhesions.adhesion",
                    ),
                ),
            ],
            options={"db_table": "integrations_membres"},
        ),
        migrations.CreateModel(
            name="AffectationMembre",
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
                ("date_debut", models.DateTimeField(default=django.utils.timezone.now)),
                ("date_fin", models.DateTimeField(blank=True, null=True)),
                ("motif_fin", models.TextField(blank=True)),
                ("cree_le", models.DateTimeField(auto_now_add=True)),
                ("modifie_le", models.DateTimeField(auto_now=True)),
                (
                    "adhesion",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="affectations",
                        to="adhesions.adhesion",
                    ),
                ),
                (
                    "attribuee_par",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="affectations_attribuees",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "departement",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="affectations_membres",
                        to="organisation.departement",
                    ),
                ),
                (
                    "poste",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="affectations_membres",
                        to="organisation.poste",
                    ),
                ),
            ],
            options={
                "db_table": "affectations_membres",
                "ordering": ("-date_debut",),
                "constraints": [
                    models.UniqueConstraint(
                        condition=models.Q(("date_fin__isnull", True)),
                        fields=("adhesion",),
                        name="affectations_une_active_par_adhesion",
                    )
                ],
            },
        ),
    ]
