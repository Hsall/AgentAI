from django.urls import path

from . import views

app_name = 'academics'

urlpatterns = [
    path('', views.tableau, name='tableau'),
    path('cours/', views.cours_liste, name='cours_liste'),
    path('cours/nouveau/', views.cours_editer, name='cours_creer'),
    path('cours/<int:cours_id>/modifier/', views.cours_editer,
         name='cours_modifier'),
    path('cours/<int:cours_id>/supprimer/', views.cours_supprimer,
         name='cours_supprimer'),
    path('documents/ajouter/', views.document_ajouter, name='document_ajouter'),
    path('documents/<int:document_id>/supprimer/', views.document_supprimer,
         name='document_supprimer'),
    path('emploi-du-temps/', views.edt_liste, name='edt_liste'),
    path('emploi-du-temps/creneau/', views.creneau_ajouter,
         name='creneau_ajouter'),
    path('emploi-du-temps/creneau/<int:creneau_id>/supprimer/',
         views.creneau_supprimer, name='creneau_supprimer'),
    path('examens/planifier/', views.examen_ajouter, name='examen_ajouter'),
    path('examens/<int:examen_id>/supprimer/', views.examen_supprimer,
         name='examen_supprimer'),
]
