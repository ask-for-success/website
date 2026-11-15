from django.contrib import admin

from .models import Departement, Poste


@admin.register(Departement)
class AdministrationDepartement(admin.ModelAdmin):
    list_display = ("nom", "est_actif", "cree_le", "modifie_le")
    list_filter = ("est_actif",)
    search_fields = ("nom", "description")
    ordering = ("nom",)


@admin.register(Poste)
class AdministrationPoste(admin.ModelAdmin):
    list_display = ("nom", "departement", "est_actif", "cree_le")
    list_filter = ("est_actif", "departement")
    search_fields = ("nom", "description", "departement__nom")
    ordering = ("departement__nom", "nom")
