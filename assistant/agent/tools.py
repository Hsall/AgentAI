"""Les tools de l'agent : chacun interroge les vraies données de l'école
(base Django) ou les supports de cours PDF déposés par l'administration.
"""

from pypdf import PdfReader
from smolagents import tool

from academics.models import Cours, CreneauEDT, Examen

from . import generation

LIMITE_TEXTE_PDF = 7000


def _trouver_cours(reference):
    """Retrouve un cours par son code exact, sinon par son intitulé."""
    reference = reference.strip()
    cours = Cours.objects.filter(code__iexact=reference).first()
    if cours is None:
        cours = Cours.objects.filter(intitule__icontains=reference).first()
    return cours


def texte_des_documents(cours):
    """Concatène le texte extrait des PDF d'un cours (tronqué)."""
    morceaux = []
    for document in cours.documents.all():
        try:
            lecteur = PdfReader(document.fichier.path)
            texte = '\n'.join(page.extract_text() or '' for page in lecteur.pages)
            morceaux.append(f'### {document.titre}\n{texte.strip()}')
        except Exception as exc:
            morceaux.append(f'### {document.titre}\n(Lecture impossible : {exc})')
    return '\n\n'.join(morceaux)[:LIMITE_TEXTE_PDF]


def contenu_pour_generation(cours):
    """Texte servant de base au résumé/quiz : les PDF, sinon la description."""
    texte = texte_des_documents(cours)
    if texte.strip():
        return texte
    return f'{cours.intitule} — {cours.description}'


@tool
def rechercher_cours(mots_cles: str) -> str:
    """Recherche des cours dans le catalogue de l'ISC Business School.

    Args:
        mots_cles: Mots-clés à chercher dans le code, l'intitulé, la
            description ou le nom de l'enseignant (ex : "marketing", "MKT101").
    """
    resultats = Cours.objects.none()
    for champ in ('code__icontains', 'intitule__icontains',
                  'description__icontains', 'enseignant__icontains'):
        resultats = resultats | Cours.objects.filter(**{champ: mots_cles.strip()})
    resultats = resultats.distinct()[:8]
    if not resultats:
        return f"Aucun cours ne correspond à « {mots_cles} » dans le catalogue."
    lignes = []
    for c in resultats:
        nb_docs = c.documents.count()
        lignes.append(
            f'- {c.code} | {c.intitule} | niveau {c.niveau}, {c.get_semestre_display()}, '
            f'{c.credits} ECTS | enseignant : {c.enseignant} | '
            f'{nb_docs} support(s) PDF disponible(s)\n  {c.description[:200]}'
        )
    return 'Cours trouvés :\n' + '\n'.join(lignes)


@tool
def consulter_emploi_du_temps(niveau: str, jour: str = '') -> str:
    """Donne l'emploi du temps hebdomadaire d'un niveau d'études.

    Args:
        niveau: Le niveau concerné parmi L1, L2, L3, M1, M2.
        jour: Optionnel. Un jour précis ("lundi", "mardi"...). Vide = toute la semaine.
    """
    creneaux = CreneauEDT.objects.filter(
        cours__niveau__iexact=niveau.strip()
    ).select_related('cours')
    if jour.strip():
        numeros = {nom.lower(): num for num, nom in CreneauEDT.Jour.choices}
        numero = numeros.get(jour.strip().lower())
        if numero is None:
            return f"Jour inconnu : « {jour} ». Utilisez lundi, mardi... samedi."
        creneaux = creneaux.filter(jour=numero)
    if not creneaux.exists():
        return f"Aucun créneau trouvé pour le niveau {niveau}" + (
            f' le {jour}.' if jour.strip() else '.')
    lignes = [
        f'- {c.get_jour_display()} {c.heure_debut:%Hh%M}–{c.heure_fin:%Hh%M} : '
        f'{c.cours.intitule} ({c.cours.code}), salle {c.salle}, '
        f'avec {c.cours.enseignant}'
        for c in creneaux
    ]
    return f'Emploi du temps {niveau} :\n' + '\n'.join(lignes)


@tool
def consulter_examens(niveau: str) -> str:
    """Liste les examens à venir (partiels, finaux, rattrapages) d'un niveau.

    Args:
        niveau: Le niveau concerné parmi L1, L2, L3, M1, M2.
    """
    from django.utils import timezone

    examens = Examen.objects.filter(
        cours__niveau__iexact=niveau.strip(), date__gte=timezone.now(),
    ).select_related('cours')[:15]
    if not examens:
        return f"Aucun examen à venir n'est planifié pour le niveau {niveau}."
    jours_fr = ['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi',
                'dimanche']
    lignes = []
    for e in examens:
        date_locale = timezone.localtime(e.date)
        lignes.append(
            f'- {jours_fr[date_locale.weekday()]} {date_locale:%d/%m/%Y à %H:%M} : '
            f'{e.get_type_examen_display()} de {e.cours.intitule} '
            f'({e.cours.code}), salle {e.salle}, durée {e.duree_minutes} min.'
            + (f' Consignes : {e.consignes}' if e.consignes else '')
        )
    return f'Examens à venir pour le niveau {niveau} :\n' + '\n'.join(lignes)


@tool
def lire_document_cours(cours: str) -> str:
    """Lit le contenu des supports de cours PDF d'une matière.

    Args:
        cours: Le code (ex : "MKT101") ou l'intitulé du cours dont il faut
            lire les supports.
    """
    objet = _trouver_cours(cours)
    if objet is None:
        return f"Aucun cours « {cours} » trouvé. Utilise d'abord rechercher_cours."
    if not objet.documents.exists():
        return (
            f"Le cours {objet.code} ({objet.intitule}) n'a aucun support PDF. "
            f'Description du cours : {objet.description}'
        )
    return (
        f'Contenu des supports du cours {objet.code} — {objet.intitule} :\n\n'
        + texte_des_documents(objet)
    )


@tool
def resumer_lecon(cours: str, niveau_etudiant: str) -> str:
    """Produit un résumé pédagogique d'un cours, adapté au niveau de l'étudiant.

    Args:
        cours: Le code (ex : "MKT101") ou l'intitulé du cours à résumer.
        niveau_etudiant: Le niveau de l'étudiant (L1, L2, L3, M1, M2) pour
            adapter la complexité du résumé.
    """
    objet = _trouver_cours(cours)
    if objet is None:
        return f"Aucun cours « {cours} » trouvé. Utilise d'abord rechercher_cours."
    return generation.generer_resume(
        objet.intitule, niveau_etudiant, contenu_pour_generation(objet),
    )


@tool
def generer_quiz(cours: str, niveau_etudiant: str, nombre_questions: int = 5) -> str:
    """Génère un quiz d'entraînement (QCM) sur un cours, avec le corrigé.

    Args:
        cours: Le code (ex : "MKT101") ou l'intitulé du cours.
        niveau_etudiant: Le niveau de l'étudiant (L1, L2, L3, M1, M2).
        nombre_questions: Nombre de questions souhaité (entre 3 et 10).
    """
    objet = _trouver_cours(cours)
    if objet is None:
        return f"Aucun cours « {cours} » trouvé. Utilise d'abord rechercher_cours."
    nombre_questions = max(3, min(int(nombre_questions), 10))
    questions = generation.generer_quiz_json(
        objet.intitule, niveau_etudiant,
        contenu_pour_generation(objet), nombre_questions,
    )
    lettres = 'ABCD'
    blocs = []
    for i, q in enumerate(questions, start=1):
        options = '\n'.join(
            f'   {lettres[j]}. {opt}' for j, opt in enumerate(q['options'])
        )
        blocs.append(
            f"**Question {i}.** {q['question']}\n{options}\n"
            f"   ✔ Réponse : {lettres[q['bonne_reponse']]} — {q['explication']}"
        )
    return f'Quiz sur {objet.intitule} ({objet.code}) :\n\n' + '\n\n'.join(blocs)


TOOLS = [
    rechercher_cours,
    consulter_emploi_du_temps,
    consulter_examens,
    lire_document_cours,
    resumer_lecon,
    generer_quiz,
]
