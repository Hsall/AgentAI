from django.db import models

from accounts.models import User


class Cours(models.Model):
    """Une matière enseignée à l'ISC Business School."""

    class Semestre(models.TextChoices):
        S1 = 'S1', 'Semestre 1'
        S2 = 'S2', 'Semestre 2'

    code = models.CharField('code', max_length=12, unique=True)
    intitule = models.CharField('intitulé', max_length=150)
    niveau = models.CharField('niveau', max_length=2, choices=User.Niveau.choices)
    semestre = models.CharField(
        'semestre', max_length=2, choices=Semestre.choices, default=Semestre.S1,
    )
    enseignant = models.CharField('enseignant', max_length=100)
    credits = models.PositiveSmallIntegerField('crédits ECTS', default=4)
    description = models.TextField('description', blank=True)

    class Meta:
        verbose_name = 'cours'
        verbose_name_plural = 'cours'
        ordering = ['niveau', 'code']

    def __str__(self):
        return f'{self.code} — {self.intitule} ({self.niveau})'


class DocumentCours(models.Model):
    """Support de cours (PDF) déposé par l'administration ou un enseignant."""

    cours = models.ForeignKey(
        Cours, verbose_name='cours', on_delete=models.CASCADE,
        related_name='documents',
    )
    titre = models.CharField('titre', max_length=200)
    fichier = models.FileField('fichier PDF', upload_to='documents_cours/')
    ajoute_le = models.DateTimeField('ajouté le', auto_now_add=True)

    class Meta:
        verbose_name = 'document de cours'
        verbose_name_plural = 'documents de cours'
        ordering = ['-ajoute_le']

    def __str__(self):
        return f'{self.titre} ({self.cours.code})'


class CreneauEDT(models.Model):
    """Un créneau de l'emploi du temps hebdomadaire."""

    class Jour(models.IntegerChoices):
        LUNDI = 1, 'Lundi'
        MARDI = 2, 'Mardi'
        MERCREDI = 3, 'Mercredi'
        JEUDI = 4, 'Jeudi'
        VENDREDI = 5, 'Vendredi'
        SAMEDI = 6, 'Samedi'

    cours = models.ForeignKey(
        Cours, verbose_name='cours', on_delete=models.CASCADE,
        related_name='creneaux',
    )
    jour = models.IntegerField('jour', choices=Jour.choices)
    heure_debut = models.TimeField('heure de début')
    heure_fin = models.TimeField('heure de fin')
    salle = models.CharField('salle', max_length=30)

    class Meta:
        verbose_name = "créneau d'emploi du temps"
        verbose_name_plural = "créneaux d'emploi du temps"
        ordering = ['jour', 'heure_debut']

    def __str__(self):
        return (
            f'{self.get_jour_display()} {self.heure_debut:%H:%M}-'
            f'{self.heure_fin:%H:%M} : {self.cours.code} ({self.salle})'
        )


class Examen(models.Model):
    """Une épreuve planifiée (partiel, final ou rattrapage)."""

    class Type(models.TextChoices):
        PARTIEL = 'PARTIEL', 'Partiel'
        FINAL = 'FINAL', 'Examen final'
        RATTRAPAGE = 'RATTRAPAGE', 'Rattrapage'

    cours = models.ForeignKey(
        Cours, verbose_name='cours', on_delete=models.CASCADE,
        related_name='examens',
    )
    type_examen = models.CharField(
        "type d'épreuve", max_length=12, choices=Type.choices,
        default=Type.PARTIEL,
    )
    date = models.DateTimeField('date et heure')
    duree_minutes = models.PositiveSmallIntegerField('durée (minutes)', default=120)
    salle = models.CharField('salle', max_length=30)
    consignes = models.TextField('consignes', blank=True)

    class Meta:
        verbose_name = 'examen'
        verbose_name_plural = 'examens'
        ordering = ['date']

    def __str__(self):
        return f'{self.get_type_examen_display()} {self.cours.code} — {self.date:%d/%m/%Y %H:%M}'
