from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse
from django.utils import timezone


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "etudiant", "Etudiant"
        COMPANY = "entreprise", "Entreprise"
        ADMIN = "administrateur", "Administrateur"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=32, choices=Role.choices, default=Role.STUDENT)


class SkillTag(models.Model):
    """Competence technique prédéfinie (ex: Python, Django, React...)."""

    class Category(models.TextChoices):
        BACKEND = "backend", "Backend"
        FRONTEND = "frontend", "Frontend"
        DATA = "data", "Data / IA"
        DEVOPS = "devops", "DevOps / Cloud"
        MOBILE = "mobile", "Mobile"
        DESIGN = "design", "Design / UX"
        OTHER = "other", "Autre"

    name = models.CharField(max_length=80, unique=True)
    category = models.CharField(
        max_length=20, choices=Category.choices, default=Category.OTHER
    )
    icon = models.CharField(max_length=40, blank=True, help_text="Classe Bootstrap Icon (bi-...)")

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return self.name


class StudentProfile(TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_profile",
    )
    universite = models.CharField(max_length=255)
    telephone = models.CharField(max_length=30, blank=True)
    specialite = models.CharField(max_length=255, blank=True)
    competences = models.TextField(blank=True)
    photo = models.FileField(upload_to="profiles/students/photos/", blank=True)
    cv_profile = models.FileField(upload_to="profiles/students/cv/", blank=True)
    # Tags de compétences cochés par l'étudiant
    skill_tags = models.ManyToManyField(
        SkillTag,
        blank=True,
        related_name="students",
        verbose_name="Compétences (tags)",
    )

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.universite}"


class CompanyProfile(TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="company_profile",
    )
    nom_entreprise = models.CharField(max_length=255)
    secteur = models.CharField(max_length=255)
    email_entreprise = models.EmailField()
    telephone = models.CharField(max_length=30, blank=True)
    adresse = models.CharField(max_length=255, blank=True)
    description_entreprise = models.TextField(blank=True)
    site_web = models.URLField(blank=True)
    logo = models.FileField(upload_to="profiles/companies/logos/", blank=True)

    def __str__(self):
        return self.nom_entreprise


class StageOffer(TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"

    class Source(models.TextChoices):
        LOCAL = "local", "Local"
        LINKEDIN = "linkedin", "LinkedIn"

    company_profile = models.ForeignKey(
        CompanyProfile,
        on_delete=models.CASCADE,
        related_name="stage_offers",
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    domain = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    duration = models.CharField(max_length=255, blank=True)
    closing_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    # Source de l'offre
    source = models.CharField(
        max_length=20, choices=Source.choices, default=Source.LOCAL
    )
    linkedin_url = models.URLField(blank=True, help_text="URL de l'offre sur LinkedIn")
    # Tags de compétences requis par l'offre
    required_tags = models.ManyToManyField(
        SkillTag,
        blank=True,
        related_name="offers",
        verbose_name="Compétences requises (tags)",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("offres_show", args=[self.pk])

    @property
    def is_open(self):
        return self.status == self.Status.ACTIVE and (
            self.closing_date is None or self.closing_date >= timezone.localdate()
        )

    @property
    def is_linkedin(self):
        return self.source == self.Source.LINKEDIN


class Application(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "en_attente", "En attente"
        ACCEPTED = "acceptee", "Acceptee"
        REJECTED = "refusee", "Refusee"

    stage_offer = models.ForeignKey(
        StageOffer,
        on_delete=models.CASCADE,
        related_name="applications",
    )
    student_profile = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name="applications",
    )
    cv = models.FileField(upload_to="applications/cv/")
    cv_original_name = models.CharField(max_length=255, blank=True)
    cover_letter = models.FileField(upload_to="applications/cover_letters/")
    cover_letter_original_name = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    applied_at = models.DateTimeField(default=timezone.now)
    ai_match_score = models.IntegerField(blank=True, null=True)
    ai_match_reasoning = models.TextField(blank=True)

    class Meta:
        ordering = ["-applied_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["stage_offer", "student_profile"],
                name="unique_application_per_offer_student",
            )
        ]

    def __str__(self):
        return f"{self.student_profile.user.email} -> {self.stage_offer.title}"

    @property
    def status_class(self):
        return {
            self.Status.ACCEPTED: "success",
            self.Status.REJECTED: "danger",
            self.Status.PENDING: "warning",
        }.get(self.status, "secondary")


class AdminActionLog(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="admin_action_logs",
    )
    action = models.CharField(max_length=80)
    target_type = models.CharField(max_length=80)
    target_id = models.PositiveBigIntegerField(blank=True, null=True)
    description = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} {self.target_type} #{self.target_id or '-'}"
