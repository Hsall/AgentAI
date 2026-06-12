from django import forms

from .models import Cours, CreneauEDT, DocumentCours, Examen


class CoursForm(forms.ModelForm):
    class Meta:
        model = Cours
        fields = ['code', 'intitule', 'niveau', 'semestre', 'enseignant',
                  'credits', 'description']
        widgets = {'description': forms.Textarea(attrs={'rows': 4})}


class DocumentForm(forms.ModelForm):
    class Meta:
        model = DocumentCours
        fields = ['cours', 'titre', 'fichier']

    def clean_fichier(self):
        fichier = self.cleaned_data['fichier']
        if fichier and not fichier.name.lower().endswith('.pdf'):
            raise forms.ValidationError('Seuls les fichiers PDF sont acceptés.')
        return fichier


class CreneauForm(forms.ModelForm):
    class Meta:
        model = CreneauEDT
        fields = ['cours', 'jour', 'heure_debut', 'heure_fin', 'salle']
        widgets = {
            'heure_debut': forms.TimeInput(attrs={'type': 'time'}),
            'heure_fin': forms.TimeInput(attrs={'type': 'time'}),
        }

    def clean(self):
        donnees = super().clean()
        debut, fin = donnees.get('heure_debut'), donnees.get('heure_fin')
        if debut and fin and fin <= debut:
            raise forms.ValidationError(
                "L'heure de fin doit être après l'heure de début.")
        return donnees


class ExamenForm(forms.ModelForm):
    class Meta:
        model = Examen
        fields = ['cours', 'type_examen', 'date', 'duree_minutes', 'salle',
                  'consignes']
        widgets = {
            'date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'consignes': forms.Textarea(attrs={'rows': 3}),
        }
