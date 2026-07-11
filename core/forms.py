from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator

from .models import Application, CompanyProfile, SkillTag, StageOffer, StudentProfile, User


FORM_CONTROL = "form-control"


def apply_bootstrap(fields):
    for field in fields.values():
        widget = field.widget
        if isinstance(widget, forms.CheckboxInput):
            widget.attrs.setdefault("class", "form-check-input")
        elif isinstance(widget, forms.CheckboxSelectMultiple):
            pass  # géré dans les templates avec styles custom
        elif isinstance(widget, forms.Select):
            widget.attrs.setdefault("class", "form-select")
        else:
            widget.attrs.setdefault("class", FORM_CONTROL)


class EmailLoginForm(AuthenticationForm):
    username = forms.EmailField(label="Email", widget=forms.EmailInput(attrs={"autofocus": True}))

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        apply_bootstrap(self.fields)

    def clean(self):
        email = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        if email and password:
            try:
                user = User.objects.get(email__iexact=email)
            except User.DoesNotExist as exc:
                raise ValidationError("Identifiants invalides.") from exc

            self.user_cache = authenticate(
                self.request,
                username=user.username,
                password=password,
            )
            if self.user_cache is None:
                raise ValidationError("Identifiants invalides.")
            self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data


class RegisterForm(forms.Form):
    name = forms.CharField(label="Nom complet", max_length=255)
    email = forms.EmailField(label="Email")
    password1 = forms.CharField(label="Mot de passe", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirmer le mot de passe", widget=forms.PasswordInput)
    role = forms.ChoiceField(
        label="Role",
        choices=[
            (User.Role.STUDENT, "Etudiant"),
            (User.Role.COMPANY, "Entreprise"),
        ],
    )
    universite = forms.CharField(label="Universite", max_length=255, required=False)
    nom_entreprise = forms.CharField(label="Nom entreprise", max_length=255, required=False)
    secteur = forms.CharField(label="Secteur", max_length=255, required=False)
    email_entreprise = forms.EmailField(label="Email entreprise", required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_bootstrap(self.fields)

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("Cet email est deja utilise.")
        return email

    def clean(self):
        cleaned = super().clean()
        role = cleaned.get("role")
        if cleaned.get("password1") != cleaned.get("password2"):
            self.add_error("password2", "La confirmation du mot de passe ne correspond pas.")

        if role == User.Role.STUDENT and not cleaned.get("universite"):
            self.add_error("universite", "L'universite est obligatoire pour un etudiant.")

        if role == User.Role.COMPANY:
            for field in ("nom_entreprise", "secteur", "email_entreprise"):
                if not cleaned.get(field):
                    self.add_error(field, "Ce champ est obligatoire pour une entreprise.")

        return cleaned

    def save(self):
        name_parts = self.cleaned_data["name"].strip().split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""
        email = self.cleaned_data["email"]

        user = User.objects.create_user(
            username=email,
            email=email,
            password=self.cleaned_data["password1"],
            first_name=first_name,
            last_name=last_name,
            role=self.cleaned_data["role"],
        )

        if user.role == User.Role.STUDENT:
            StudentProfile.objects.create(
                user=user,
                universite=self.cleaned_data["universite"],
            )
        else:
            CompanyProfile.objects.create(
                user=user,
                nom_entreprise=self.cleaned_data["nom_entreprise"],
                secteur=self.cleaned_data["secteur"],
                email_entreprise=self.cleaned_data["email_entreprise"],
            )

        return user


class StudentProfileForm(forms.Form):
    name = forms.CharField(label="Nom complet", max_length=255)
    email = forms.EmailField(label="Email")
    universite = forms.CharField(label="Universite", max_length=255)
    telephone = forms.CharField(label="Telephone", max_length=30, required=False)
    specialite = forms.CharField(label="Specialite", max_length=255, required=False)
    competences = forms.CharField(label="Competences libres", widget=forms.Textarea, required=False)
    cv_profile = forms.FileField(
        label="CV du profil",
        required=False,
        validators=[FileExtensionValidator(["pdf", "doc", "docx"])],
    )
    photo = forms.FileField(
        label="Photo de profil",
        required=False,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp"])],
    )
    delete_photo = forms.BooleanField(label="Supprimer la photo", required=False)

    def __init__(self, user, *args, **kwargs):
        self.user = user
        self.profile = user.student_profile
        initial = kwargs.pop("initial", {})
        initial.update(
            {
                "name": user.get_full_name() or user.username,
                "email": user.email,
                "universite": self.profile.universite,
                "telephone": self.profile.telephone,
                "specialite": self.profile.specialite,
                "competences": self.profile.competences,
            }
        )
        super().__init__(*args, initial=initial, **kwargs)
        apply_bootstrap(self.fields)

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        exists = User.objects.filter(email__iexact=email).exclude(pk=self.user.pk).exists()
        if exists:
            raise ValidationError("Cet email est deja utilise.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        # Le CV est obligatoire si l'étudiant n'en a pas déjà un
        cv_profile = cleaned_data.get("cv_profile")
        if not cv_profile and not self.profile.cv_profile:
            self.add_error("cv_profile", "Vous devez uploader un CV pour que l'IA puisse analyser vos compétences.")
        return cleaned_data

    def save(self):
        name_parts = self.cleaned_data["name"].strip().split(" ", 1)
        self.user.first_name = name_parts[0]
        self.user.last_name = name_parts[1] if len(name_parts) > 1 else ""
        self.user.email = self.cleaned_data["email"]
        self.user.username = self.cleaned_data["email"]
        self.user.save()

        self.profile.universite = self.cleaned_data["universite"]
        self.profile.telephone = self.cleaned_data["telephone"]
        self.profile.specialite = self.cleaned_data["specialite"]
        self.profile.competences = self.cleaned_data["competences"]
        if self.cleaned_data.get("delete_photo"):
            self.profile.photo.delete(save=False)
            self.profile.photo = ""
        if self.cleaned_data.get("photo"):
            self.profile.photo = self.cleaned_data["photo"]
        if self.cleaned_data.get("cv_profile"):
            self.profile.cv_profile = self.cleaned_data["cv_profile"]
        self.profile.save()

        return self.profile


class CompanyProfileForm(forms.Form):
    name = forms.CharField(label="Nom du responsable", max_length=255)
    email = forms.EmailField(label="Email utilisateur")
    nom_entreprise = forms.CharField(label="Nom entreprise", max_length=255)
    secteur = forms.CharField(label="Secteur", max_length=255)
    email_entreprise = forms.EmailField(label="Email entreprise")
    telephone = forms.CharField(label="Telephone", max_length=30, required=False)
    adresse = forms.CharField(label="Adresse", max_length=255, required=False)
    description_entreprise = forms.CharField(
        label="Description de l'entreprise",
        widget=forms.Textarea,
        required=False,
    )
    site_web = forms.URLField(label="Site web", required=False)
    logo = forms.FileField(
        label="Logo entreprise",
        required=False,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp", "svg"])],
    )
    delete_logo = forms.BooleanField(label="Supprimer le logo", required=False)

    def __init__(self, user, *args, **kwargs):
        self.user = user
        self.profile = user.company_profile
        initial = kwargs.pop("initial", {})
        initial.update(
            {
                "name": user.get_full_name() or user.username,
                "email": user.email,
                "nom_entreprise": self.profile.nom_entreprise,
                "secteur": self.profile.secteur,
                "email_entreprise": self.profile.email_entreprise,
                "telephone": self.profile.telephone,
                "adresse": self.profile.adresse,
                "description_entreprise": self.profile.description_entreprise,
                "site_web": self.profile.site_web,
            }
        )
        super().__init__(*args, initial=initial, **kwargs)
        apply_bootstrap(self.fields)

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        exists = User.objects.filter(email__iexact=email).exclude(pk=self.user.pk).exists()
        if exists:
            raise ValidationError("Cet email est deja utilise.")
        return email

    def save(self):
        name_parts = self.cleaned_data["name"].strip().split(" ", 1)
        self.user.first_name = name_parts[0]
        self.user.last_name = name_parts[1] if len(name_parts) > 1 else ""
        self.user.email = self.cleaned_data["email"]
        self.user.username = self.cleaned_data["email"]
        self.user.save()

        for field in (
            "nom_entreprise",
            "secteur",
            "email_entreprise",
            "telephone",
            "adresse",
            "description_entreprise",
            "site_web",
        ):
            setattr(self.profile, field, self.cleaned_data[field])
        if self.cleaned_data.get("delete_logo"):
            self.profile.logo.delete(save=False)
            self.profile.logo = ""
        if self.cleaned_data.get("logo"):
            self.profile.logo = self.cleaned_data["logo"]
        self.profile.save()
        return self.profile


class StageOfferForm(forms.ModelForm):
    required_tags = forms.ModelMultipleChoiceField(
        label="Compétences requises (tags)",
        queryset=SkillTag.objects.all().order_by("category", "name"),
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )

    class Meta:
        model = StageOffer
        fields = ["title", "description", "domain", "location", "duration", "closing_date", "status", "required_tags"]
        labels = {
            "title": "Titre",
            "description": "Description",
            "domain": "Domaine",
            "location": "Localisation",
            "duration": "Duree",
            "closing_date": "Date de cloture",
            "status": "Statut",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 6}),
            "closing_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_bootstrap(self.fields)
        if self.instance and self.instance.pk:
            self.fields["required_tags"].initial = self.instance.required_tags.all()


class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ["cv", "cover_letter"]

    cv = forms.FileField(
        label="CV",
        validators=[FileExtensionValidator(["pdf", "doc", "docx"])],
    )
    cover_letter = forms.FileField(
        label="Lettre de motivation",
        validators=[FileExtensionValidator(["pdf", "doc", "docx"])],
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_bootstrap(self.fields)


class LinkedInImportForm(forms.Form):
    """Formulaire pour déclencher l'import LinkedIn depuis l'interface Admin."""
    query = forms.CharField(
        label="Mots-clés de recherche",
        max_length=200,
        initial="stage PFE informatique",
        widget=forms.TextInput(attrs={"placeholder": "ex: stage PFE informatique"}),
    )
    location = forms.CharField(
        label="Localisation",
        max_length=100,
        initial="Maroc",
        widget=forms.TextInput(attrs={"placeholder": "ex: Casablanca, Maroc"}),
    )
    max_results = forms.IntegerField(
        label="Nombre max d'offres",
        initial=20,
        min_value=1,
        max_value=100,
    )
    hours_old = forms.IntegerField(
        label="Ancienneté max (heures)",
        initial=168,
        min_value=24,
        max_value=720,
        help_text="168 h = 7 jours",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_bootstrap(self.fields)
