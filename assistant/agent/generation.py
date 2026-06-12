"""Appels directs aux modèles Hugging Face (hors orchestration smolagents).

Utilisé par les tools de l'agent (résumé, quiz) et par les vues qui génèrent
des contenus structurés (simulation d'examen, fiches de révision).
"""

import json
import re

from django.conf import settings
from huggingface_hub import InferenceClient


class AgentIndisponible(Exception):
    """Levée quand le modèle Hugging Face ne peut pas être appelé."""


def _client():
    if not settings.HF_TOKEN:
        raise AgentIndisponible(
            "Aucun token Hugging Face configuré. Créez un fichier .env à la "
            "racine du projet contenant : HF_TOKEN=hf_votre_token"
        )
    return InferenceClient(model=settings.GENERATION_MODEL_ID, token=settings.HF_TOKEN)


def appeler_modele(messages, max_tokens=1500):
    """Envoie une conversation au modèle de génération et renvoie sa réponse texte."""
    try:
        client = _client()
        reponse = client.chat_completion(messages=messages, max_tokens=max_tokens)
        return reponse.choices[0].message.content
    except AgentIndisponible:
        raise
    except Exception as exc:
        raise AgentIndisponible(
            f"Le modèle Hugging Face est injoignable ({exc.__class__.__name__}). "
            "Vérifiez votre connexion internet et votre token HF."
        ) from exc


def _extraire_json(texte):
    """Isole le premier tableau JSON d'une réponse de modèle (avec ou sans ```)."""
    match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', texte, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    debut, fin = texte.find('['), texte.rfind(']')
    if debut == -1 or fin == -1:
        raise ValueError('Aucun tableau JSON trouvé dans la réponse du modèle.')
    return json.loads(texte[debut:fin + 1])


def generer_resume(titre_cours, niveau, contenu):
    """Résume un support de cours, adapté au niveau de l'étudiant."""
    messages = [
        {'role': 'system', 'content': (
            "Tu es un assistant pédagogique de l'ISC Business School. "
            "Tu rédiges des résumés de cours clairs, structurés en markdown, "
            f"adaptés à un étudiant de niveau {niveau}. Réponds en français."
        )},
        {'role': 'user', 'content': (
            f"Résume ce support du cours « {titre_cours} » en dégageant les "
            f"notions clés, avec des titres et des listes :\n\n{contenu[:8000]}"
        )},
    ]
    return appeler_modele(messages)


def generer_quiz_json(titre_cours, niveau, contenu, nombre_questions=5):
    """Génère un QCM sous forme de liste de dictionnaires Python.

    Chaque question : {"question", "options" (4 choix), "bonne_reponse"
    (index 0-3), "explication"}.
    """
    messages = [
        {'role': 'system', 'content': (
            "Tu es un générateur de QCM pour l'ISC Business School. Tu réponds "
            "UNIQUEMENT avec un tableau JSON valide, sans aucun texte autour."
        )},
        {'role': 'user', 'content': (
            f"Génère {nombre_questions} questions de QCM en français sur le cours "
            f"« {titre_cours} », pour un étudiant de niveau {niveau}.\n"
            "Format STRICT : un tableau JSON d'objets avec les clés "
            '"question" (str), "options" (liste de 4 str), '
            '"bonne_reponse" (entier 0-3), "explication" (str courte).\n\n'
            f"Contenu du cours :\n{contenu[:8000]}"
        )},
    ]
    brut = appeler_modele(messages, max_tokens=2500)
    questions = _extraire_json(brut)
    # Validation minimale : on écarte les questions mal formées plutôt que planter.
    valides = [
        q for q in questions
        if isinstance(q.get('question'), str)
        and isinstance(q.get('options'), list) and len(q['options']) == 4
        and isinstance(q.get('bonne_reponse'), int) and 0 <= q['bonne_reponse'] <= 3
    ]
    if not valides:
        raise AgentIndisponible('Le modèle a renvoyé un quiz invalide, réessayez.')
    for q in valides:
        q.setdefault('explication', '')
    return valides


def generer_fiche(titre_cours, niveau, contenu):
    """Génère une fiche de révision structurée en markdown."""
    messages = [
        {'role': 'system', 'content': (
            "Tu es un coach de révision de l'ISC Business School. Tu produis des "
            "fiches de révision synthétiques en markdown, en français, adaptées "
            f"à un étudiant de niveau {niveau}."
        )},
        {'role': 'user', 'content': (
            f"Rédige une fiche de révision du cours « {titre_cours} » avec : "
            "« L'essentiel à retenir » (5 à 8 points), « Définitions clés », "
            "« Pièges classiques » et « 3 questions pour s'auto-tester ».\n\n"
            f"Contenu du cours :\n{contenu[:8000]}"
        )},
    ]
    return appeler_modele(messages, max_tokens=2000)
