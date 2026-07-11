from django.test import TestCase
from django.urls import reverse

from .forms import RegisterForm
from .models import CompanyProfile, StageOffer, StudentProfile, User
from .services import match_offer_for_student


class StageHubSmokeTests(TestCase):
    def test_matching_engine_scores_relevant_offer(self):
        student_user = User.objects.create_user(
            username="student@example.com",
            email="student@example.com",
            password="password123",
            role=User.Role.STUDENT,
        )
        student = StudentProfile.objects.create(
            user=student_user,
            universite="Universite Hassan II",
            specialite="Django",
            competences="Python Django SQL",
        )
        company_user = User.objects.create_user(
            username="company@example.com",
            email="company@example.com",
            password="password123",
            role=User.Role.COMPANY,
        )
        company = CompanyProfile.objects.create(
            user=company_user,
            nom_entreprise="Atlas Digital",
            secteur="Tech",
            email_entreprise="contact@atlas.test",
        )
        offer = StageOffer.objects.create(
            company_profile=company,
            title="Stage Django",
            description="Developpement web avec Django",
            domain="Web",
            location="Casablanca",
        )

        self.assertGreater(match_offer_for_student(offer, student), 0)

    def test_student_registration_form_creates_profile(self):
        form = RegisterForm(
            data={
                "name": "Yasmine Etudiante",
                "email": "student@example.com",
                "password1": "password123",
                "password2": "password123",
                "role": User.Role.STUDENT,
                "universite": "Universite Hassan II",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.assertTrue(User.objects.filter(email="student@example.com").exists())
        self.assertTrue(StudentProfile.objects.filter(user__email="student@example.com").exists())

    def test_student_registration_redirects_to_dashboard_without_email_verification(self):
        response = self.client.post(
            reverse("register"),
            {
                "name": "Nouvelle Etudiante",
                "email": "new-student@example.com",
                "password1": "password123",
                "password2": "password123",
                "role": User.Role.STUDENT,
                "universite": "Universite Test",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("student_dashboard"))

# Create your tests here.
