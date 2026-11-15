from django.contrib import admin

from .models import Adhesion, AffectationMembre, IntegrationMembre, InvitationAdhesion


@admin.register(Adhesion)
class AdministrationAdhesion(admin.ModelAdmin):
    list_display = ("utilisateur", "etat", "acceptee_le", "modifie_le")
    list_filter = ("etat",)
    search_fields = ("utilisateur__email", "utilisateur__first_name", "utilisateur__last_name")
    ordering = ("-acceptee_le",)


@admin.register(IntegrationMembre)
class AdministrationIntegrationMembre(admin.ModelAdmin):
    list_display = ("adhesion", "etat", "commencee_le", "terminee_le")
    list_filter = ("etat",)
    search_fields = ("adhesion__utilisateur__email",)


@admin.register(AffectationMembre)
class AdministrationAffectationMembre(admin.ModelAdmin):
    list_display = (
        "adhesion",
        "departement",
        "poste",
        "date_debut",
        "date_fin",
        "attribuee_par",
    )
    list_filter = ("departement", "poste")
    search_fields = (
        "adhesion__utilisateur__email",
        "departement__nom",
        "poste__nom",
    )
    ordering = ("-date_debut",)


@admin.register(InvitationAdhesion)
class AdministrationInvitationAdhesion(admin.ModelAdmin):
    list_display = (
        "utilisateur",
        "etat",
        "expire_le",
        "creee_par",
        "creee_le",
    )
    list_filter = ("etat",)
    search_fields = (
        "utilisateur__email",
        "utilisateur__first_name",
        "utilisateur__last_name",
    )
    readonly_fields = (
        "empreinte_jeton",
        "creee_le",
        "modifiee_le",
        "utilisee_le",
        "annulee_le",
    )
    ordering = ("-creee_le",)
