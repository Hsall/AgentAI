# Boussole — Agent IA académique de l'ISC Business School

Agent IA éducatif interne à l'ISC Business School, construit avec
**smolagents** (orchestration) et des **modèles Hugging Face** (raisonnement),
servi par une application web **Django** complète avec un mode étudiant et un
mode administration.

L'agent comprend une question académique en langage naturel, identifie le
besoin (cours, examen, planning, résumé, quiz, conseil), **choisit lui-même les
bons tools**, et adapte le niveau de sa réponse au profil de l'étudiant
(L1 → M2). Surtout : ses tools interrogent **la vraie base de données de
l'école** (cours, emplois du temps, examens) et lisent **les vrais supports
PDF** déposés par l'administration — il ne répond jamais avec des horaires ou
des salles inventés.

---

## 1. Description de l'agent

Boussole couvre quatre rôles du sujet :

| Rôle | Ce qu'il fait | Tools mobilisés |
|---|---|---|
| **Assistant pédagogique** | Explique les notions en s'appuyant sur les supports PDF du cours | `lire_document_cours`, `rechercher_cours` |
| **Assistant académique** | Emploi du temps, salles, dates et consignes d'examens | `consulter_emploi_du_temps`, `consulter_examens` |
| **Coach de révision** | Résumés de leçons, quiz d'entraînement, fiches de révision | `resumer_lecon`, `generer_quiz` |
| **Conseiller étudiant** | Orientation, méthode de travail, organisation | (réponse directe, sans tool) |

L'adaptation au niveau est systématique : le profil de l'utilisateur connecté
(prénom, niveau L1/L2/L3/M1/M2, rôle) est injecté dans le contexte de chaque
requête, et les instructions de l'agent lui imposent d'ajuster sa pédagogie.

## 2. Architecture smolagents

```
Question en langage naturel (interface web Django)
        │
        ▼
assistant/agent/engine.py
  ToolCallingAgent (smolagents)
  └─ modèle : InferenceClientModel → Qwen/Qwen2.5-72B-Instruct (API HF)
  └─ contexte injecté : profil utilisateur + date + historique de conversation
        │  l'agent raisonne, choisit et enchaîne ses tools (max 6 étapes)
        ▼
assistant/agent/tools.py — 6 tools @tool branchés sur Django
  ├─ rechercher_cours(mots_cles)            → ORM Cours
  ├─ consulter_emploi_du_temps(niveau, jour) → ORM CreneauEDT
  ├─ consulter_examens(niveau)              → ORM Examen
  ├─ lire_document_cours(cours)             → pypdf sur les PDF uploadés
  ├─ resumer_lecon(cours, niveau)           → PDF + 2ᵉ appel modèle HF
  └─ generer_quiz(cours, niveau, n)         → PDF + 2ᵉ appel modèle HF (JSON)
        │
        ▼
Réponse markdown structurée → sauvegardée en base (historique) → rendue dans le chat
```

Deux usages distincts des modèles Hugging Face :

- **`engine.py`** : le modèle *pilote* (`AGENT_MODEL_ID`) raisonne et décide
  des appels de tools via `ToolCallingAgent` ;
- **`generation.py`** : un modèle de *génération* (`GENERATION_MODEL_ID`,
  configurable indépendamment) produit les résumés, les QCM au format JSON
  strict et les fiches de révision. C'est aussi lui qu'utilisent la simulation
  d'examen et les fiches, hors orchestration, pour un format garanti.

## 3. Les tools (≥ 3 exigés, 6 fournis)

| Tool | Source de vérité | Exemple de question déclencheuse |
|---|---|---|
| `rechercher_cours` | base de données des cours | « qui enseigne le marketing ? » |
| `consulter_emploi_du_temps` | créneaux saisis par la scolarité | « j'ai quoi lundi matin ? » |
| `consulter_examens` | examens planifiés | « c'est quand le partiel de compta ? » |
| `lire_document_cours` | PDF déposés par l'administration | « explique-moi le chapitre 3 de marketing » |
| `resumer_lecon` | PDF + modèle HF | « résume-moi le cours d'éco internationale » |
| `generer_quiz` | PDF + modèle HF | « fais-moi un quiz de 5 questions sur la compta » |

## 4. Fonctionnalités

**Obligatoires (sujet)** — toutes couvertes : compréhension du langage
naturel, identification du besoin, choix automatique des tools, réponse
structurée (markdown), adaptation au niveau L1→M2.

**Bonus implémentés :**

- ✅ Interface web (Django, un cran au-dessus de Flask/Streamlit : auth,
  ORM, sessions, upload de fichiers)
- ✅ Mode **étudiant** vs **administration** (deux espaces, droits séparés)
- ✅ Génération automatique de **fiches de révision** (imprimables)
- ✅ **Simulation d'examen** chronométrée avec correction automatique et
  note sur 20
- ✅ **Historique des interactions** (conversations persistées, reprises,
  suppression)

## 5. Installation

```bash
git clone <ce-repo>
cd ISCAGENTProject
pip install -r requirements.txt

# Token Hugging Face (gratuit) : https://huggingface.co/settings/tokens
copy .env .env        # puis mettre votre HF_TOKEN dans .env

python manage.py migrate
python manage.py peupler_demo   # cours, EDT, examens, PDF et comptes de démo
python manage.py runserver
```

Ouvrir <http://127.0.0.1:8000/>.

| Compte | Mot de passe | Rôle |
|---|---|---|
| `amine` | `iscdemo2026` | Étudiant L3 |
| `lina` | `iscdemo2026` | Étudiante M1 |
| `scolarite` | `iscdemo2026` | Administration (+ accès `/admin/`) |

Vérification rapide sans token HF : `python smoke_test.py` (pages + tools de
base de données). Le token n'est nécessaire que pour les réponses du modèle.

## 6. Cas d'usage réels à l'ISC Business School

1. **Avant les partiels** — Amine (L3) demande « c'est quand le partiel de
   compta et j'ai droit à quoi ? » → l'agent appelle `consulter_examens`,
   répond avec la date, la salle, la durée et les consignes saisies par la
   scolarité.
2. **Révision active** — « fais-moi un quiz de 5 questions sur les coûts
   complets » → `generer_quiz` lit le PDF du chapitre déposé par
   l'enseignant et produit un QCM corrigé ; pour une épreuve formelle,
   l'étudiant passe par la page *Examens blancs* (chronomètre + note /20).
3. **Rattrapage d'un cours manqué** — « résume-moi le chapitre 3 de
   marketing » → `resumer_lecon` produit une synthèse adaptée au niveau L3,
   transformable en fiche imprimable.
4. **Organisation quotidienne** — « j'ai quoi demain ? » → l'agent croise la
   date du jour (injectée dans le contexte) et `consulter_emploi_du_temps`.
5. **Côté scolarité** — la scolarité dépose un nouveau PDF ou déplace un
   examen dans son espace : l'agent répond immédiatement avec les nouvelles
   données, sans redéploiement.

## 7. Structure du code

```
ISCAGENTProject/
├── accounts/        # utilisateur personnalisé (rôle, niveau), connexion
├── academics/       # cours, documents PDF, EDT, examens + espace administration
│   └── management/commands/peupler_demo.py   # données de démonstration
├── assistant/       # chat, historique, examens blancs, fiches
│   └── agent/       # engine.py (smolagents), tools.py (6 tools), generation.py
├── templates/       # interface (design « papier & encre » maison)
├── static/css/      # feuille de style artisanale, sans framework
├── notebook_test_agent.ipynb   # notebook de test (livrable)
└── smoke_test.py    # vérification pages + tools sans token
```

## 8. Notes de conception

- **Pourquoi Django plutôt que Streamlit/Flask ?** Le sujet les propose en
  bonus ; Django apporte nativement l'authentification (mode
  étudiant/administration), l'ORM (les tools lisent la vraie base), l'upload
  de fichiers et l'admin. C'est ce qui permet à l'agent d'être branché sur des
  données vivantes plutôt que sur un jeu de données figé.
- **Design** : interface dessinée à la main (palette papier/encre/rouille,
  typographies Fraunces + Public Sans + Caveat, ombres franches, tampons,
  soulignements irréguliers, copie d'examen avec marge rouge) — volontairement
  loin des templates génériques.
- **Robustesse** : si le token HF est absent ou l'API injoignable, l'interface
  reste utilisable et le chat affiche un message d'erreur explicite plutôt
  qu'une page blanche.
