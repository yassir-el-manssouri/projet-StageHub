from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import CompanyProfile, StageOffer, StudentProfile, User


class Command(BaseCommand):
    help = "Create demo accounts and offers for local exploration."

    def handle(self, *args, **options):
        admin = self._user(
            "admin@example.com",
            "Admin StageHub",
            User.Role.ADMIN,
            is_staff=True,
            is_superuser=True,
        )
        student = self._user("etudiant@example.com", "Yasmine Etudiante", User.Role.STUDENT)
        company_user = self._user("entreprise@example.com", "Nadia Recruteur", User.Role.COMPANY)

        StudentProfile.objects.update_or_create(
            user=student,
            defaults={
                "universite": "Universite Hassan II",
                "telephone": "0600000000",
                "specialite": "Developpement web",
                "competences": "Python Django SQL Bootstrap HTML CSS",
            },
        )
        company, _ = CompanyProfile.objects.update_or_create(
            user=company_user,
            defaults={
                "nom_entreprise": "Atlas Digital",
                "secteur": "Technologies",
                "email_entreprise": "contact@atlas-digital.test",
                "telephone": "0522000000",
                "adresse": "Casablanca",
                "description_entreprise": "Entreprise specialisee dans les produits web et data.",
                "site_web": "https://example.com",
            },
        )

        offers = [
            {
                "title": "Stage developpeur Django",
                "description": "Participation au developpement d'une plateforme web avec Python, Django, Bootstrap et SQL.",
                "domain": "Developpement web",
                "location": "Casablanca",
                "duration": "3 mois",
            },
            {
                "title": "Stage data et automatisation",
                "description": "Analyse de donnees, automatisation de workflows et creation de tableaux de bord internes.",
                "domain": "Data",
                "location": "Rabat",
                "duration": "4 mois",
            },
        ]
        for item in offers:
            StageOffer.objects.update_or_create(
                company_profile=company,
                title=item["title"],
                defaults={
                    **item,
                    "status": StageOffer.Status.ACTIVE,
                    "closing_date": timezone.localdate() + timedelta(days=30),
                },
            )

        self.stdout.write(self.style.SUCCESS("Demo prete. Mot de passe pour tous: password123"))
        self.stdout.write("Comptes: admin@example.com, etudiant@example.com, entreprise@example.com")

    def _user(self, email, full_name, role, **flags):
        first_name, _, last_name = full_name.partition(" ")
        user, _ = User.objects.update_or_create(
            email=email,
            defaults={
                "username": email,
                "first_name": first_name,
                "last_name": last_name,
                "role": role,
                **flags,
            },
        )
        user.set_password("password123")
        for key, value in flags.items():
            setattr(user, key, value)
        user.save()
        return user
