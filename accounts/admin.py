from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class UtilisateurAdmin(UserAdmin):
    list_display = ('username', 'first_name', 'last_name', 'role', 'niveau')
    list_filter = ('role', 'niveau')
    fieldsets = UserAdmin.fieldsets + (
        ('Profil ISC', {'fields': ('role', 'niveau')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Profil ISC', {'fields': ('role', 'niveau')}),
    )
