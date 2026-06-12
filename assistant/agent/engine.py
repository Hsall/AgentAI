"""Orchestration de l'agent avec smolagents.

L'agent reçoit la question de l'étudiant en langage naturel, identifie le
besoin (cours, examen, résumé, planning, quiz, conseil...) et décide seul
quels tools appeler avant de formuler sa réponse.
"""

from django.conf import settings
from smolagents import InferenceClientModel, ToolCallingAgent

from .generation import AgentIndisponible
from .tools import TOOLS

INSTRUCTIONS = """Tu es « Boussole », l'assistant IA interne de l'ISC Business School.
Tu accompagnes les étudiants et l'administration dans la vie académique :
- assistant pédagogique : expliquer les notions des cours (appuie-toi sur les supports PDF) ;
- assistant académique : emplois du temps, examens, salles, enseignants ;
- coach de révision : résumés, quiz, méthodes de révision ;
- conseiller étudiant : orientation, organisation, motivation.

Règles :
1. Réponds toujours en français, de manière claire et structurée (markdown).
2. Utilise les tools pour répondre avec les vraies données de l'école ;
   n'invente jamais un horaire, une salle ou une date d'examen.
3. Adapte ton niveau d'explication au profil de l'étudiant indiqué dans la
   question (un L1 a besoin de plus de pédagogie qu'un M2).
4. Si une information est introuvable dans les données, dis-le honnêtement et
   suggère de contacter la scolarité.
5. Pour les questions d'orientation ou de méthode, tu peux répondre sans tool,
   avec des conseils concrets et bienveillants.
"""


def _construire_agent():
    if not settings.HF_TOKEN:
        raise AgentIndisponible(
            "Aucun token Hugging Face configuré. Créez un fichier .env à la "
            "racine du projet contenant : HF_TOKEN=hf_votre_token"
        )
    modele = InferenceClientModel(
        model_id=settings.AGENT_MODEL_ID,
        token=settings.HF_TOKEN,
    )
    return ToolCallingAgent(
        tools=TOOLS,
        model=modele,
        max_steps=settings.AGENT_MAX_STEPS,
        instructions=INSTRUCTIONS,
    )


def _contexte_utilisateur(utilisateur):
    from django.utils import timezone

    aujourd_hui = timezone.localtime().strftime('%A %d %B %Y, %H:%M')
    if utilisateur.est_administration:
        profil = "membre de l'administration de l'ISC"
    else:
        profil = f'étudiant(e) de niveau {utilisateur.niveau or "inconnu"}'
    return (
        f"[Contexte : tu parles à {utilisateur.prenom_affiche}, {profil}. "
        f"Nous sommes le {aujourd_hui}.]"
    )


def _contexte_historique(historique):
    """Réinjecte les derniers échanges pour garder le fil de la conversation."""
    if not historique:
        return ''
    lignes = []
    for message in historique:
        role = 'Étudiant' if message.auteur == message.Auteur.UTILISATEUR else 'Toi'
        lignes.append(f'{role} : {message.contenu[:400]}')
    return '[Rappel des échanges précédents :\n' + '\n'.join(lignes) + ']\n\n'


def _tools_appeles(agent):
    """Extrait les noms des tools réellement appelés pendant le run."""
    noms = []
    try:
        for etape in agent.memory.steps:
            for appel in (getattr(etape, 'tool_calls', None) or []):
                nom = getattr(appel, 'name', None)
                if nom and nom not in noms and nom != 'final_answer':
                    noms.append(nom)
    except Exception:
        pass
    return noms


def repondre(question, utilisateur, historique=None):
    """Fait tourner l'agent et renvoie (réponse, liste des tools utilisés).

    Lève AgentIndisponible si le modèle Hugging Face n'est pas joignable,
    afin que la vue affiche un message d'erreur propre.
    """
    agent = _construire_agent()
    tache = (
        f'{_contexte_utilisateur(utilisateur)}\n\n'
        f'{_contexte_historique(historique)}'
        f'Question : {question}'
    )
    try:
        resultat = agent.run(tache)
    except AgentIndisponible:
        raise
    except Exception as exc:
        raise AgentIndisponible(
            f"L'agent n'a pas pu traiter la demande ({exc.__class__.__name__} : {exc})."
        ) from exc
    return str(resultat), _tools_appeles(agent)
