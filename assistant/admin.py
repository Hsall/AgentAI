from django.contrib import admin

from .models import Conversation, FicheRevision, Message, SimulationExamen


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ('auteur', 'contenu', 'tools_utilises', 'envoye_le')


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('titre', 'utilisateur', 'creee_le', 'mise_a_jour_le')
    inlines = [MessageInline]


@admin.register(SimulationExamen)
class SimulationExamenAdmin(admin.ModelAdmin):
    list_display = ('cours', 'etudiant', 'note_sur_20', 'commencee_le', 'terminee_le')
    list_filter = ('cours',)


@admin.register(FicheRevision)
class FicheRevisionAdmin(admin.ModelAdmin):
    list_display = ('cours', 'etudiant', 'creee_le')
    list_filter = ('cours',)
