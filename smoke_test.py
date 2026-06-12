"""Vérification rapide : toutes les pages répondent correctement.
Lancement : python smoke_test.py
"""
import os
import sys

import django

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ISCAGENTProject.settings')
django.setup()

from django.test import Client  # noqa: E402
from django.test.utils import setup_test_environment  # noqa: E402

setup_test_environment()

erreurs = []


def verifier(client, url, attendu=200, nom=''):
    reponse = client.get(url)
    statut = reponse.status_code
    ok = statut == attendu
    print(f'  {"OK " if ok else "ECHEC"} [{statut}] {url} {nom}')
    if not ok:
        erreurs.append((url, statut, attendu))
    return reponse


print('— Anonyme (doit rediriger vers la connexion) —')
anonyme = Client()
verifier(anonyme, '/', 302)
verifier(anonyme, '/assistant/', 302)
verifier(anonyme, '/compte/connexion/', 200)

print('— Étudiant (amine) —')
etudiant = Client()
assert etudiant.login(username='amine', password='iscdemo2026'), 'login étudiant KO'
verifier(etudiant, '/', 200, '(tableau de bord)')
verifier(etudiant, '/assistant/', 200, '(chat)')
verifier(etudiant, '/examens-blancs/', 200)
verifier(etudiant, '/fiches/', 200)
verifier(etudiant, '/administration/', 302, '(accès refusé → redirection)')

print('— Administration (scolarite) —')
admin = Client()
assert admin.login(username='scolarite', password='iscdemo2026'), 'login admin KO'
verifier(admin, '/', 302, '(redirigé vers administration)')
verifier(admin, '/administration/', 200, '(tableau scolarité)')
verifier(admin, '/administration/cours/', 200)
verifier(admin, '/administration/cours/nouveau/', 200)
verifier(admin, '/administration/emploi-du-temps/', 200)
verifier(admin, '/administration/documents/ajouter/', 200)
verifier(admin, '/administration/examens/planifier/', 200)

print('— Tools de l\'agent (sans modèle, données réelles) —')
from assistant.agent import tools  # noqa: E402

resultat = tools.rechercher_cours('marketing')
print('  rechercher_cours("marketing") →', resultat.splitlines()[1][:80])
assert 'MKT301' in resultat

resultat = tools.consulter_emploi_du_temps('L3', 'lundi')
print('  consulter_emploi_du_temps("L3","lundi") →', resultat.splitlines()[1][:80])
assert 'B204' in resultat

resultat = tools.consulter_examens('L3')
print('  consulter_examens("L3") →', resultat.splitlines()[1][:80])
assert 'Partiel' in resultat

resultat = tools.lire_document_cours('MKT301')
print('  lire_document_cours("MKT301") →', resultat[:80].replace('\n', ' '))
assert 'segmentation' in resultat.lower()

if erreurs:
    raise SystemExit(f'{len(erreurs)} échec(s) : {erreurs}')
print('\nTout est bon : pages et tools fonctionnent.')
