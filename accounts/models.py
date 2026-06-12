from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Utilisateur de la plateforme : étudiant ou membre de l'administration."""

    class Role(models.TextChoices):
        ETUDIANT = 'ETUDIANT', 'Étudiant'
        ADMINISTRATION = 'ADMINISTRATION', 'Administration'

    class Niveau(models.TextChoices):
        L1 = 'L1', 'Licence 1'
        L2 = 'L2', 'Licence 2'
        L3 = 'L3', 'Licence 3'
        M1 = 'M1', 'Master 1'
        M2 = 'M2', 'Master 2'

    role = models.CharField(
        'rôle', max_length=20, choices=Role.choices, default=Role.ETUDIANT,
    )
    niveau = models.CharField(
        "niveau d'études", max_length=2, choices=Niveau.choices,
        blank=True, help_text='Uniquement pour les étudiants.',
    )

    @property
    def est_administration(self):
        return self.role == self.Role.ADMINISTRATION

    @property
    def prenom_affiche(self):
        return self.first_name or self.username

    def __str__(self):
        nom = self.get_full_name() or self.username
        if self.role == self.Role.ETUDIANT and self.niveau:
            return f'{nom} ({self.niveau})'
        return nom
