from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import User
from assistant.models import Conversation, SimulationExamen

from .forms import CoursForm, CreneauForm, DocumentForm, ExamenForm
from .models import Cours, CreneauEDT, DocumentCours, Examen


def administration_requise(vue):
    """Réserve une vue aux comptes du mode administration."""

    @wraps(vue)
    @login_required
    def enveloppe(request, *args, **kwargs):
        if not request.user.est_administration:
            messages.error(request, 'Cet espace est réservé à l\'administration.')
            return redirect('assistant:tableau_de_bord')
        return vue(request, *args, **kwargs)

    return enveloppe


@administration_requise
def tableau(request):
    return render(request, 'administration/tableau.html', {
        'nb_cours': Cours.objects.count(),
        'nb_documents': DocumentCours.objects.count(),
        'nb_etudiants': User.objects.filter(role=User.Role.ETUDIANT).count(),
        'nb_conversations': Conversation.objects.count(),
        'examens_a_venir': Examen.objects.filter(
            date__gte=timezone.now()).select_related('cours')[:6],
        'derniers_documents': DocumentCours.objects.select_related('cours')[:5],
        'dernieres_simulations': SimulationExamen.objects.select_related(
            'cours', 'etudiant')[:5],
    })


# --- Cours -----------------------------------------------------------------

@administration_requise
def cours_liste(request):
    return render(request, 'administration/cours_liste.html', {
        'liste_cours': Cours.objects.prefetch_related('documents', 'creneaux'),
    })


@administration_requise
def cours_editer(request, cours_id=None):
    cours = get_object_or_404(Cours, pk=cours_id) if cours_id else None
    form = CoursForm(request.POST or None, instance=cours)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(
            request, 'Cours modifié.' if cours else 'Cours créé.')
        return redirect('academics:cours_liste')
    return render(request, 'administration/formulaire.html', {
        'form': form,
        'titre': f'Modifier {cours.code}' if cours else 'Nouveau cours',
        'retour': 'academics:cours_liste',
    })


@administration_requise
@require_POST
def cours_supprimer(request, cours_id):
    cours = get_object_or_404(Cours, pk=cours_id)
    cours.delete()
    messages.success(request, f'Cours {cours.code} supprimé.')
    return redirect('academics:cours_liste')


# --- Documents PDF ---------------------------------------------------------

@administration_requise
def document_ajouter(request):
    form = DocumentForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        document = form.save()
        messages.success(
            request,
            f'Support « {document.titre} » ajouté au cours {document.cours.code}. '
            "L'agent peut maintenant le lire.",
        )
        return redirect('academics:cours_liste')
    return render(request, 'administration/formulaire.html', {
        'form': form,
        'titre': 'Déposer un support de cours (PDF)',
        'retour': 'academics:cours_liste',
        'fichier': True,
    })


@administration_requise
@require_POST
def document_supprimer(request, document_id):
    document = get_object_or_404(DocumentCours, pk=document_id)
    document.delete()
    messages.success(request, 'Support supprimé.')
    return redirect('academics:cours_liste')


# --- Emploi du temps -------------------------------------------------------

@administration_requise
def edt_liste(request):
    return render(request, 'administration/edt_liste.html', {
        'creneaux': CreneauEDT.objects.select_related('cours'),
        'examens': Examen.objects.select_related('cours'),
    })


@administration_requise
def creneau_ajouter(request):
    form = CreneauForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Créneau ajouté à l'emploi du temps.")
        return redirect('academics:edt_liste')
    return render(request, 'administration/formulaire.html', {
        'form': form,
        'titre': 'Ajouter un créneau',
        'retour': 'academics:edt_liste',
    })


@administration_requise
@require_POST
def creneau_supprimer(request, creneau_id):
    get_object_or_404(CreneauEDT, pk=creneau_id).delete()
    messages.success(request, 'Créneau supprimé.')
    return redirect('academics:edt_liste')


# --- Examens ----------------------------------------------------------------

@administration_requise
def examen_ajouter(request):
    form = ExamenForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Examen planifié.')
        return redirect('academics:edt_liste')
    return render(request, 'administration/formulaire.html', {
        'form': form,
        'titre': 'Planifier un examen',
        'retour': 'academics:edt_liste',
    })


@administration_requise
@require_POST
def examen_supprimer(request, examen_id):
    get_object_or_404(Examen, pk=examen_id).delete()
    messages.success(request, 'Examen supprimé.')
    return redirect('academics:edt_liste')
