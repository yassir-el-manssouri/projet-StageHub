from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    AdminActionLog,
    Application,
    CompanyProfile,
    SkillTag,
    StageOffer,
    StudentProfile,
    User,
)


@admin.register(SkillTag)
class SkillTagAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "icon")
    list_filter = ("category",)
    search_fields = ("name",)


@admin.register(User)
class StageHubUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("StageHub", {"fields": ("role",)}),
    )
    list_display = ("username", "email", "first_name", "last_name", "role")
    list_filter = UserAdmin.list_filter + ("role",)
    search_fields = ("username", "email", "first_name", "last_name")


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "universite", "specialite", "telephone")
    search_fields = ("user__email", "user__first_name", "user__last_name", "universite", "specialite")
    filter_horizontal = ("skill_tags",)


@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display = ("nom_entreprise", "secteur", "email_entreprise", "user")
    search_fields = ("nom_entreprise", "secteur", "email_entreprise", "user__email")


@admin.register(StageOffer)
class StageOfferAdmin(admin.ModelAdmin):
    list_display = ("title", "company_profile", "domain", "location", "status", "source", "closing_date")
    list_filter = ("status", "source", "domain", "location")
    search_fields = ("title", "description", "domain", "location", "company_profile__nom_entreprise")
    filter_horizontal = ("required_tags",)


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("stage_offer", "student_profile", "status", "applied_at")
    list_filter = ("status", "applied_at")
    search_fields = ("stage_offer__title", "student_profile__user__email")


@admin.register(AdminActionLog)
class AdminActionLogAdmin(admin.ModelAdmin):
    list_display = ("action", "target_type", "target_id", "user", "ip_address", "created_at")
    list_filter = ("action", "target_type", "created_at")
    search_fields = ("description", "user__email")
