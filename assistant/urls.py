from django.urls import path

from . import views

app_name = 'assistant'

urlpatterns = [
    path('', views.tableau_de_bord, name='tableau_de_bord'),
    # Chat avec l'agent
    path('assistant/', views.chat, name='chat'),
    path('assistant/conversation/<int:conversation_id>/', views.chat,
         name='conversation'),
    path('assistant/envoyer/', views.envoyer_message, name='envoyer_message'),
    path('assistant/conversation/<int:conversation_id>/supprimer/',
         views.supprimer_conversation, name='supprimer_conversation'),
    # Examens blancs
    path('examens-blancs/', views.examens_blancs, name='examens_blancs'),
    path('examens-blancs/demarrer/', views.demarrer_simulation,
         name='demarrer_simulation'),
    path('examens-blancs/<int:simulation_id>/', views.passer_simulation,
         name='passer_simulation'),
    path('examens-blancs/<int:simulation_id>/corriger/',
         views.corriger_simulation, name='corriger_simulation'),
    path('examens-blancs/<int:simulation_id>/resultat/',
         views.resultat_simulation, name='resultat_simulation'),
    # Fiches de révision
    path('fiches/', views.fiches, name='fiches'),
    path('fiches/generer/', views.generer_fiche, name='generer_fiche'),
    path('fiches/<int:fiche_id>/', views.fiche_detail, name='fiche_detail'),
    path('fiches/<int:fiche_id>/supprimer/', views.supprimer_fiche,
         name='supprimer_fiche'),
]
