from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.defaultfilters import truncatechars
from django.utils import timezone
from django.views.decorators.http import require_POST

import markdown as md

from academics.models import Cours, CreneauEDT, Examen

from .agent import engine, generation
from .agent.tools import contenu_pour_generation
from .models import Conversation, FicheRevision, Message, SimulationExamen


def _markdown(texte):
    return md.markdown(texte, extensions=['extra', 'sane_lists'])


def _cours_du_niveau(utilisateur):
    if utilisateur.est_administration:
        return Cours.objects.all()
    return Cours.objects.filter(niveau=utilisateur.niveau)


# --- Tableau de bord -------------------------------------------------------

@login_required
def tableau_de_bord(request):
    utilisateur = request.user
    if utilisateur.est_administration:
        return redirect('academics:tableau')

    aujourd_hui = timezone.localtime()
    creneaux_du_jour = CreneauEDT.objects.filter(
        cours__niveau=utilisateur.niveau, jour=aujourd_hui.isoweekday(),
    ).select_related('cours')
    examens_a_venir = Examen.objects.filter(
        cours__niveau=utilisateur.niveau, date__gte=aujourd_hui,
    ).select_related('cours')[:4]
    return render(request, 'assistant/tableau_de_bord.html', {
        'creneaux_du_jour': creneaux_du_jour,
        'examens_a_venir': examens_a_venir,
        'conversations_recentes': utilisateur.conversations.all()[:4],
        'dernieres_fiches': utilisateur.fiches.select_related('cours')[:3],
        'cours_du_niveau': _cours_du_niveau(utilisateur),
    })


# --- Chat avec l'agent -----------------------------------------------------

@login_required
def chat(request, conversation_id=None):
    conversations = request.user.conversations.all()
    conversation = None
    if conversation_id is not None:
        conversation = get_object_or_404(
            Conversation, pk=conversation_id, utilisateur=request.user,
        )
    contenu_messages = []
    if conversation:
        contenu_messages = [
            {'objet': m, 'html': _markdown(m.contenu)}
            for m in conversation.messages.all()
        ]
    return render(request, 'assistant/chat.html', {
        'conversations': conversations,
        'conversation': conversation,
        'contenu_messages': contenu_messages,
    })


@login_required
@require_POST
def envoyer_message(request):
    question = request.POST.get('question', '').strip()
    if not question:
        return JsonResponse({'erreur': 'Message vide.'}, status=400)

    conversation_id = request.POST.get('conversation_id') or None
    if conversation_id:
        conversation = get_object_or_404(
            Conversation, pk=conversation_id, utilisateur=request.user,
        )
    else:
        conversation = Conversation.objects.create(
            utilisateur=request.user, titre=truncatechars(question, 60),
        )

    historique = list(conversation.messages.order_by('-envoye_le')[:6])[::-1]
    Message.objects.create(
        conversation=conversation,
        auteur=Message.Auteur.UTILISATEUR,
        contenu=question,
    )

    try:
        reponse, tools = engine.repondre(question, request.user, historique)
    except generation.AgentIndisponible as exc:
        reponse, tools = (
            f"⚠ Je n'arrive pas à joindre mon modèle de langage.\n\n{exc}", []
        )

    Message.objects.create(
        conversation=conversation,
        auteur=Message.Auteur.AGENT,
        contenu=reponse,
        tools_utilises=', '.join(tools)[:250],
    )
    conversation.save()  # rafraîchit mise_a_jour_le

    return JsonResponse({
        'conversation_id': conversation.pk,
        'reponse_html': _markdown(reponse),
        'tools': tools,
    })


@login_required
@require_POST
def supprimer_conversation(request, conversation_id):
    conversation = get_object_or_404(
        Conversation, pk=conversation_id, utilisateur=request.user,
    )
    conversation.delete()
    messages.success(request, 'Conversation supprimée.')
    return redirect('assistant:chat')


# --- Simulation d'examen ---------------------------------------------------

@login_required
def examens_blancs(request):
    return render(request, 'assistant/examens_liste.html', {
        'simulations': request.user.simulations.select_related('cours'),
        'cours_disponibles': _cours_du_niveau(request.user),
    })


@login_required
@require_POST
def demarrer_simulation(request):
    cours = get_object_or_404(Cours, pk=request.POST.get('cours_id'))
    nombre = max(3, min(int(request.POST.get('nombre_questions', 5)), 10))
    niveau = request.user.niveau or cours.niveau
    try:
        questions = generation.generer_quiz_json(
            cours.intitule, niveau, contenu_pour_generation(cours), nombre,
        )
    except (generation.AgentIndisponible, ValueError) as exc:
        messages.error(request, f"Impossible de générer l'examen blanc : {exc}")
        return redirect('assistant:examens_blancs')
    simulation = SimulationExamen.objects.create(
        etudiant=request.user, cours=cours, questions=questions,
    )
    return redirect('assistant:passer_simulation', simulation.pk)


@login_required
def passer_simulation(request, simulation_id):
    simulation = get_object_or_404(
        SimulationExamen, pk=simulation_id, etudiant=request.user,
    )
    if simulation.est_terminee:
        return redirect('assistant:resultat_simulation', simulation.pk)
    duree_minutes = max(2 * len(simulation.questions), 5)
    return render(request, 'assistant/examen_passer.html', {
        'simulation': simulation,
        'duree_minutes': duree_minutes,
    })


@login_required
@require_POST
def corriger_simulation(request, simulation_id):
    simulation = get_object_or_404(
        SimulationExamen, pk=simulation_id, etudiant=request.user,
    )
    if not simulation.est_terminee:
        reponses = {}
        for i in range(len(simulation.questions)):
            valeur = request.POST.get(f'question_{i}')
            if valeur is not None and valeur != '':
                reponses[str(i)] = int(valeur)
        simulation.corriger(reponses)
    return redirect('assistant:resultat_simulation', simulation.pk)


@login_required
def resultat_simulation(request, simulation_id):
    simulation = get_object_or_404(
        SimulationExamen, pk=simulation_id, etudiant=request.user,
    )
    if not simulation.est_terminee:
        return redirect('assistant:passer_simulation', simulation.pk)
    lettres = 'ABCD'
    detail = []
    for i, q in enumerate(simulation.questions):
        choisie = (simulation.reponses or {}).get(str(i))
        detail.append({
            'question': q['question'],
            'bonne_lettre': lettres[q['bonne_reponse']],
            'bonne_texte': q['options'][q['bonne_reponse']],
            'choisie_lettre': lettres[choisie] if choisie is not None else '—',
            'choisie_texte': q['options'][choisie] if choisie is not None else 'aucune réponse',
            'correcte': choisie == q['bonne_reponse'],
            'explication': q.get('explication', ''),
        })
    return render(request, 'assistant/examen_resultat.html', {
        'simulation': simulation,
        'detail': detail,
    })


# --- Fiches de révision ----------------------------------------------------

@login_required
def fiches(request):
    return render(request, 'assistant/fiches_liste.html', {
        'fiches': request.user.fiches.select_related('cours'),
        'cours_disponibles': _cours_du_niveau(request.user),
    })


@login_required
@require_POST
def generer_fiche(request):
    cours = get_object_or_404(Cours, pk=request.POST.get('cours_id'))
    niveau = request.user.niveau or cours.niveau
    try:
        contenu = generation.generer_fiche(
            cours.intitule, niveau, contenu_pour_generation(cours),
        )
    except generation.AgentIndisponible as exc:
        messages.error(request, f'Impossible de générer la fiche : {exc}')
        return redirect('assistant:fiches')
    fiche = FicheRevision.objects.create(
        etudiant=request.user, cours=cours, contenu=contenu,
    )
    return redirect('assistant:fiche_detail', fiche.pk)


@login_required
def fiche_detail(request, fiche_id):
    fiche = get_object_or_404(FicheRevision, pk=fiche_id, etudiant=request.user)
    return render(request, 'assistant/fiche_detail.html', {
        'fiche': fiche,
        'contenu_html': _markdown(fiche.contenu),
    })


@login_required
@require_POST
def supprimer_fiche(request, fiche_id):
    fiche = get_object_or_404(FicheRevision, pk=fiche_id, etudiant=request.user)
    fiche.delete()
    messages.success(request, 'Fiche supprimée.')
    return redirect('assistant:fiches')
