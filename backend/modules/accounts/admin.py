from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Company, User


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)


@admin.register(User)
class AccountUserAdmin(UserAdmin):
    # Alta de usuarios adicionales de una empresa: el admin de plataforma asigna empresa y rol.
    fieldsets = UserAdmin.fieldsets + (('Empresa', {'fields': ('company', 'role')}),)
    add_fieldsets = UserAdmin.add_fieldsets + (('Empresa', {'fields': ('company', 'role')}),)
    list_display = UserAdmin.list_display + ('company', 'role')
    list_filter = UserAdmin.list_filter + ('company',)
