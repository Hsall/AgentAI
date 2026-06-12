"""Peuple la base avec des données de démonstration réalistes pour l'ISC :
comptes, cours, emplois du temps, examens et supports PDF lisibles par l'agent.

Usage : python manage.py peupler_demo
"""

import datetime
import io

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone
from fpdf import FPDF
from fpdf.enums import XPos, YPos

from academics.models import Cours, CreneauEDT, DocumentCours, Examen
from accounts.models import User

MOT_DE_PASSE_DEMO = 'iscdemo2026'


def _latin1(texte):
    """Ramène le texte aux caractères supportés par les polices PDF de base."""
    remplacements = {'—': '-', '–': '-', '’': "'", '‘': "'", '“': '"',
                     '”': '"', '…': '...', 'œ': 'oe', 'Œ': 'Oe'}
    for avant, apres in remplacements.items():
        texte = texte.replace(avant, apres)
    return texte.encode('latin-1', errors='replace').decode('latin-1')


def _pdf(titre, sections):
    """Construit un petit PDF de cours (titre + sections (sous-titre, texte))."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    gauche = dict(new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('helvetica', 'B', 16)
    pdf.multi_cell(0, 9, 'ISC Business School', **gauche)
    pdf.set_font('helvetica', 'B', 13)
    pdf.multi_cell(0, 8, _latin1(titre), **gauche)
    pdf.ln(4)
    for sous_titre, texte in sections:
        pdf.set_font('helvetica', 'B', 12)
        pdf.multi_cell(0, 7, _latin1(sous_titre), **gauche)
        pdf.ln(1)
        pdf.set_font('helvetica', '', 11)
        pdf.multi_cell(0, 6, _latin1(texte), **gauche)
        pdf.ln(3)
    return bytes(pdf.output())


CONTENU_MARKETING = [
    ("1. Pourquoi segmenter un marché ?",
     "Un marché n'est jamais homogène : les consommateurs different par leurs "
     "besoins, leurs comportements d'achat, leur sensibilité au prix et leurs "
     "canaux préférés. Segmenter consiste à découper le marché en groupes "
     "homogènes (les segments) afin d'adapter l'offre, le discours et les "
     "ressources de l'entreprise. Une segmentation réussie doit produire des "
     "segments mesurables, substantiels (assez grands pour être rentables), "
     "accessibles et actionnables."),
    ("2. Les critères de segmentation",
     "On distingue quatre familles de critères. Les critères "
     "sociodémographiques (âge, revenu, profession, composition du foyer) "
     "sont simples à mesurer mais expliquent de moins en moins les "
     "comportements. Les critères géographiques (pays, climat, urbain/rural) "
     "restent décisifs pour la distribution. Les critères psychographiques "
     "(styles de vie, valeurs, personnalité) éclairent le 'pourquoi' de "
     "l'achat. Enfin les critères comportementaux (fréquence d'achat, "
     "fidélité, avantages recherchés, statut d'utilisateur) sont souvent les "
     "plus prédictifs : c'est la base du scoring RFM (récence, fréquence, "
     "montant)."),
    ("3. Le ciblage",
     "Une fois les segments identifiés, l'entreprise évalue leur attractivité "
     "(taille, croissance, intensité concurrentielle, coût d'accès) et sa "
     "propre capacité à les servir. Trois stratégies sont possibles : le "
     "marketing indifférencié (une seule offre pour tout le marché), le "
     "marketing différencié (une offre par segment retenu) et le marketing "
     "concentré ou de niche (toutes les ressources sur un seul segment). Le "
     "choix dépend des ressources de l'entreprise et de l'hétérogénéité du "
     "marché."),
    ("4. Le positionnement",
     "Le positionnement est la place qu'occupe l'offre dans l'esprit du "
     "client cible par rapport aux concurrents. Il se formule en une phrase : "
     "pour qui, contre qui, quelle promesse, quelle preuve. Un bon "
     "positionnement est crédible, distinctif, durable et simple. L'outil "
     "classique de visualisation est la carte perceptuelle (mapping) à deux "
     "dimensions, par exemple prix perçu / qualité perçue. Le triangle d'or "
     "du positionnement vérifie la cohérence entre attentes des clients, "
     "atouts de l'offre et positionnement des concurrents."),
    ("À retenir",
     "Segmentation, ciblage, positionnement (STP) forment la démarche "
     "stratégique du marketing : découper, choisir, occuper une place. Sans "
     "STP, le marketing opérationnel (les 4P) navigue à vue."),
]

CONTENU_COMPTA = [
    ("1. De la comptabilité générale à la comptabilité de gestion",
     "La comptabilité générale produit une information légale et normalisée "
     "destinée aux tiers. La comptabilité de gestion, elle, est tournée vers "
     "le pilotage interne : elle répond à la question 'combien coûte "
     "réellement ce produit, ce service, cette activité ?'. Elle est "
     "facultative mais indispensable pour fixer un prix, décider de "
     "sous-traiter ou abandonner un produit."),
    ("2. Charges directes et indirectes",
     "Une charge directe peut être affectée sans ambiguïté au coût d'un "
     "produit : matières premières consommées, main-d'oeuvre dédiée. Une "
     "charge indirecte concerne plusieurs produits à la fois (loyer de "
     "l'usine, salaire du responsable qualité, énergie) et doit transiter "
     "par un calcul intermédiaire avant d'être imputée. Toute la difficulté "
     "de la méthode des coûts complets tient au traitement de ces charges "
     "indirectes."),
    ("3. La méthode des centres d'analyse",
     "Les charges indirectes sont d'abord réparties entre des centres "
     "d'analyse (approvisionnement, production, distribution, "
     "administration) : c'est la répartition primaire. Les centres "
     "auxiliaires (entretien, gestion du personnel) déversent ensuite leurs "
     "coûts dans les centres principaux : c'est la répartition secondaire. "
     "Chaque centre principal choisit une unité d'oeuvre (heure machine, "
     "heure de main-d'oeuvre, quantité achetée) qui mesure son activité. Le "
     "coût d'unité d'oeuvre = total des charges du centre / nombre d'unités "
     "d'oeuvre."),
    ("4. Du coût d'achat au coût de revient",
     "Le calcul s'enchaîne en cascade : coût d'achat (prix d'achat + frais "
     "d'approvisionnement), puis coût de production (coût d'achat des "
     "matières consommées + charges directes et indirectes de production), "
     "puis coût de revient (coût de production des produits vendus + frais "
     "de distribution). Le résultat analytique = prix de vente - coût de "
     "revient. La somme des résultats analytiques doit se réconcilier avec "
     "le résultat de la comptabilité générale."),
    ("Limites et à retenir",
     "La méthode des coûts complets repose sur des clés de répartition "
     "parfois arbitraires et peut être faussée par la sous-activité : elle "
     "est complétée par l'imputation rationnelle ou la méthode ABC. À "
     "retenir : direct/indirect, centres d'analyse, unité d'oeuvre, cascade "
     "des coûts."),
]

CONTENU_ECO = [
    ("1. Pourquoi les nations échangent-elles ?",
     "Adam Smith montre qu'un pays a intérêt à se spécialiser là où il "
     "détient un avantage absolu. Ricardo va plus loin avec l'avantage "
     "comparatif : même un pays moins efficace en tout gagne à l'échange "
     "s'il se spécialise dans l'activité où son désavantage est le plus "
     "faible. Le modèle HOS explique les spécialisations par les dotations "
     "en facteurs de production : un pays exporte les biens intensifs dans "
     "le facteur qu'il possède en abondance."),
    ("2. Libre-échange et protectionnisme",
     "Le libre-échange élargit les marchés, intensifie la concurrence et "
     "baisse les prix, mais expose les secteurs fragiles. Les instruments "
     "protectionnistes sont les droits de douane, les quotas, les normes et "
     "les subventions. L'argument du protectionnisme éducateur (List) "
     "justifie une protection temporaire des industries naissantes. Depuis "
     "1995, l'OMC encadre les échanges et arbitre les différends "
     "commerciaux."),
    ("3. Balance des paiements et taux de change",
     "La balance des paiements enregistre l'ensemble des flux entre "
     "résidents et non-résidents : balance courante (biens, services, "
     "revenus), compte de capital et compte financier. Le taux de change "
     "résulte de l'offre et de la demande de devises ; une monnaie qui se "
     "déprécie renchérit les importations mais stimule les exportations "
     "(sous les conditions de la courbe en J et du théorème des élasticités "
     "critiques)."),
]


class Command(BaseCommand):
    help = 'Crée les comptes, cours, plannings, examens et PDF de démonstration.'

    def handle(self, *args, **options):
        self._creer_comptes()
        cours = self._creer_cours()
        self._creer_edt(cours)
        self._creer_examens(cours)
        self._creer_documents(cours)
        self.stdout.write(self.style.SUCCESS(
            '\nDonnées de démo en place. Comptes : '
            f'amine / {MOT_DE_PASSE_DEMO} (étudiant L3), '
            f'lina / {MOT_DE_PASSE_DEMO} (étudiante M1), '
            f'scolarite / {MOT_DE_PASSE_DEMO} (administration).'
        ))

    def _creer_comptes(self):
        comptes = [
            dict(username='amine', first_name='Amine', last_name='Ben Salah',
                 role=User.Role.ETUDIANT, niveau=User.Niveau.L3),
            dict(username='lina', first_name='Lina', last_name='Mansour',
                 role=User.Role.ETUDIANT, niveau=User.Niveau.M1),
            dict(username='scolarite', first_name='Nadia', last_name='Karoui',
                 role=User.Role.ADMINISTRATION, is_staff=True, is_superuser=True),
        ]
        for donnees in comptes:
            utilisateur, cree = User.objects.get_or_create(
                username=donnees['username'], defaults=donnees,
            )
            if cree:
                utilisateur.set_password(MOT_DE_PASSE_DEMO)
                utilisateur.save()
                self.stdout.write(f'  compte créé : {utilisateur.username}')

    def _creer_cours(self):
        catalogue = [
            ('MKT301', 'Marketing stratégique', 'L3', 'S1', 'Mme Dupont-Riviere', 5,
             "Segmentation, ciblage, positionnement, analyse concurrentielle et "
             "construction d'un plan marketing."),
            ('CPT301', 'Comptabilité de gestion', 'L3', 'S1', 'M. Lefranc', 5,
             "Coûts complets, centres d'analyse, coûts partiels et seuil de "
             "rentabilité pour le pilotage de l'entreprise."),
            ('ECO301', 'Économie internationale', 'L3', 'S1', 'Mme Haddad', 4,
             'Théories du commerce international, politiques commerciales, '
             'balance des paiements et taux de change.'),
            ('MGT301', 'Management des organisations', 'L3', 'S2', 'M. Okonkwo', 4,
             'Structures organisationnelles, théories des organisations, '
             'motivation et leadership.'),
            ('NEG301', 'Techniques de négociation', 'L3', 'S2', 'Mme Valette', 3,
             'Préparation, conduite et clôture d\'une négociation commerciale ; '
             'négociation raisonnée de Harvard.'),
            ('STR501', "Stratégie d'entreprise", 'M1', 'S1', 'M. Berthier', 6,
             'Diagnostic stratégique, avantage concurrentiel, croissance et '
             'stratégies de portefeuille.'),
            ('FIN501', "Finance d'entreprise", 'M1', 'S1', 'Mme N\'Diaye', 6,
             "Analyse financière, choix d'investissement, structure de "
             'financement et politique de dividende.'),
        ]
        cours = {}
        for code, intitule, niveau, semestre, enseignant, credits, description in catalogue:
            objet, cree = Cours.objects.get_or_create(code=code, defaults=dict(
                intitule=intitule, niveau=niveau, semestre=semestre,
                enseignant=enseignant, credits=credits, description=description,
            ))
            cours[code] = objet
            if cree:
                self.stdout.write(f'  cours créé : {objet}')
        return cours

    def _creer_edt(self, cours):
        if CreneauEDT.objects.exists():
            return
        h = datetime.time
        creneaux = [
            ('MKT301', 1, h(9, 0), h(12, 0), 'B204'),
            ('CPT301', 1, h(14, 0), h(16, 0), 'A102'),
            ('ECO301', 2, h(9, 0), h(11, 0), 'C310'),
            ('NEG301', 2, h(14, 0), h(17, 0), 'B112'),
            ('MGT301', 3, h(10, 0), h(13, 0), 'B204'),
            ('CPT301', 4, h(9, 0), h(11, 0), 'A102'),
            ('MKT301', 4, h(14, 0), h(16, 0), 'Amphi 2'),
            ('ECO301', 5, h(9, 0), h(12, 0), 'C310'),
            ('STR501', 1, h(9, 30), h(12, 30), 'M101'),
            ('FIN501', 3, h(14, 0), h(17, 0), 'M102'),
            ('STR501', 5, h(14, 0), h(16, 0), 'M101'),
        ]
        for code, jour, debut, fin, salle in creneaux:
            CreneauEDT.objects.create(
                cours=cours[code], jour=jour,
                heure_debut=debut, heure_fin=fin, salle=salle,
            )
        self.stdout.write(f'  {len(creneaux)} créneaux d\'emploi du temps créés')

    def _creer_examens(self, cours):
        if Examen.objects.exists():
            return
        maintenant = timezone.now().replace(minute=0, second=0, microsecond=0)
        examens = [
            ('MKT301', 'PARTIEL', 6, 9, 120, 'Amphi 1',
             'Documents interdits, calculatrice autorisée.'),
            ('CPT301', 'PARTIEL', 9, 14, 180, 'Amphi 2',
             'Plan comptable fourni avec le sujet.'),
            ('ECO301', 'FINAL', 16, 9, 180, 'Amphi 1', ''),
            ('STR501', 'PARTIEL', 11, 10, 240, 'M101',
             'Étude de cas : une page de notes manuscrites autorisée.'),
        ]
        for code, type_examen, jours, heure, duree, salle, consignes in examens:
            Examen.objects.create(
                cours=cours[code], type_examen=type_examen,
                date=(maintenant + datetime.timedelta(days=jours)).replace(hour=heure),
                duree_minutes=duree, salle=salle, consignes=consignes,
            )
        self.stdout.write(f'  {len(examens)} examens planifiés')

    def _creer_documents(self, cours):
        if DocumentCours.objects.exists():
            return
        documents = [
            ('MKT301', 'Chapitre 3 — Segmentation, ciblage, positionnement',
             CONTENU_MARKETING),
            ('CPT301', 'Chapitre 2 — La méthode des coûts complets',
             CONTENU_COMPTA),
            ('ECO301', 'Chapitre 1 — Les fondements du commerce international',
             CONTENU_ECO),
        ]
        for code, titre, sections in documents:
            contenu = _pdf(f'{cours[code].intitule} — {titre}', sections)
            document = DocumentCours(cours=cours[code], titre=titre)
            document.fichier.save(f'{code.lower()}_support.pdf',
                                  ContentFile(contenu), save=True)
            self.stdout.write(f'  PDF généré : {titre}')
