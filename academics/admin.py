from django.contrib import admin

from .models import Cours, CreneauEDT, DocumentCours, Examen


class DocumentInline(admin.TabularInline):
    model = DocumentCours
    extra = 0


class CreneauInline(admin.TabularInline):
    model = CreneauEDT
    extra = 0


@admin.register(Cours)
class CoursAdmin(admin.ModelAdmin):
    list_display = ('code', 'intitule', 'niveau', 'semestre', 'enseignant', 'credits')
    list_filter = ('niveau', 'semestre')
    search_fields = ('code', 'intitule', 'enseignant')
    inlines = [DocumentInline, CreneauInline]


@admin.register(DocumentCours)
class DocumentCoursAdmin(admin.ModelAdmin):
    list_display = ('titre', 'cours', 'ajoute_le')
    list_filter = ('cours__niveau',)


@admin.register(CreneauEDT)
class CreneauEDTAdmin(admin.ModelAdmin):
    list_display = ('cours', 'jour', 'heure_debut', 'heure_fin', 'salle')
    list_filter = ('jour', 'cours__niveau')


@admin.register(Examen)
class ExamenAdmin(admin.ModelAdmin):
    list_display = ('cours', 'type_examen', 'date', 'salle', 'duree_minutes')
    list_filter = ('type_examen', 'cours__niveau')
