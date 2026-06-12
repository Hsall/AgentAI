from django.conf import settings
from django.db import models

from academics.models import Cours


class Conversation(models.Model):
    """Un fil de discussion entre un utilisateur et l'agent."""

    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name='utilisateur',
        on_delete=models.CASCADE, related_name='conversations',
    )
    titre = models.CharField('titre', max_length=120, default='Nouvelle conversation')
    creee_le = models.DateTimeField('créée le', auto_now_add=True)
    mise_a_jour_le = models.DateTimeField('mise à jour le', auto_now=True)

    class Meta:
        verbose_name = 'conversation'
        ordering = ['-mise_a_jour_le']

    def __str__(self):
        return f'{self.titre} ({self.utilisateur.username})'


class Message(models.Model):
    """Un message dans une conversation (question ou réponse de l'agent)."""

    class Auteur(models.TextChoices):
        UTILISATEUR = 'UTILISATEUR', 'Utilisateur'
        AGENT = 'AGENT', 'Agent'

    conversation = models.ForeignKey(
        Conversation, verbose_name='conversation',
        on_delete=models.CASCADE, related_name='messages',
    )
    auteur = models.CharField('auteur', max_length=12, choices=Auteur.choices)
    contenu = models.TextField('contenu')
    tools_utilises = models.CharField(
        'tools utilisés', max_length=250, blank=True,
        help_text="Noms des tools appelés par l'agent pour produire cette réponse.",
    )
    envoye_le = models.DateTimeField('envoyé le', auto_now_add=True)

    class Meta:
        verbose_name = 'message'
        ordering = ['envoye_le']

    def __str__(self):
        return f'[{self.auteur}] {self.contenu[:50]}'


class SimulationExamen(models.Model):
    """Un examen blanc généré par l'agent, avec correction automatique."""

    etudiant = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name='étudiant',
        on_delete=models.CASCADE, related_name='simulations',
    )
    cours = models.ForeignKey(
        Cours, verbose_name='cours', on_delete=models.CASCADE,
        related_name='simulations',
    )
    # Liste de questions : [{"question", "options": [...], "bonne_reponse": 0,
    #                        "explication"}]
    questions = models.JSONField('questions')
    # Réponses de l'étudiant : {"0": 2, "1": 0, ...} (index de l'option choisie)
    reponses = models.JSONField('réponses', null=True, blank=True)
    note_sur_20 = models.DecimalField(
        'note sur 20', max_digits=4, decimal_places=2, null=True, blank=True,
    )
    commencee_le = models.DateTimeField('commencée le', auto_now_add=True)
    terminee_le = models.DateTimeField('terminée le', null=True, blank=True)

    class Meta:
        verbose_name = "simulation d'examen"
        verbose_name_plural = "simulations d'examen"
        ordering = ['-commencee_le']

    @property
    def est_terminee(self):
        return self.terminee_le is not None

    def corriger(self, reponses):
        """Corrige la copie et enregistre la note sur 20."""
        from django.utils import timezone

        self.reponses = reponses
        bonnes = sum(
            1 for i, q in enumerate(self.questions)
            if reponses.get(str(i)) == q['bonne_reponse']
        )
        self.note_sur_20 = round(20 * bonnes / len(self.questions), 2)
        self.terminee_le = timezone.now()
        self.save()
        return self.note_sur_20

    def __str__(self):
        return f'Examen blanc {self.cours.code} — {self.etudiant.username}'


class FicheRevision(models.Model):
    """Une fiche de révision générée automatiquement pour un cours."""

    etudiant = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name='étudiant',
        on_delete=models.CASCADE, related_name='fiches',
    )
    cours = models.ForeignKey(
        Cours, verbose_name='cours', on_delete=models.CASCADE,
        related_name='fiches',
    )
    contenu = models.TextField('contenu (markdown)')
    creee_le = models.DateTimeField('créée le', auto_now_add=True)

    class Meta:
        verbose_name = 'fiche de révision'
        verbose_name_plural = 'fiches de révision'
        ordering = ['-creee_le']

    def __str__(self):
        return f'Fiche {self.cours.code} — {self.etudiant.username}'
