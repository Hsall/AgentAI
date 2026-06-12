from django import template

register = template.Library()


@register.filter
def split_virgule(valeur):
    """Découpe une chaîne « a, b, c » en liste pour l'affichage des tools."""
    return [morceau.strip() for morceau in valeur.split(',') if morceau.strip()]
