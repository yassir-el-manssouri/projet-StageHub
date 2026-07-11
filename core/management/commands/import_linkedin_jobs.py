"""
Commande Django : import_linkedin_jobs
Utilisation :
    python manage.py import_linkedin_jobs
    python manage.py import_linkedin_jobs --query "stage PFE" --location "Maroc" --max-results 30
    python manage.py import_linkedin_jobs --query "stage informatique" --location "Casablanca" --max-results 20
"""

import re

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from core.models import CompanyProfile, SkillTag, StageOffer

User = get_user_model()

# Mapping mots-clés → SkillTag.name pour auto-détection des compétences dans les descriptions
KEYWORD_TAG_MAP = {
    "python": "Python",
    "django": "Django",
    "flask": "Flask",
    "fastapi": "FastAPI",
    "java": "Java",
    "spring": "Spring Boot",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "react": "React",
    "vue": "Vue.js",
    "angular": "Angular",
    "node": "Node.js",
    "nodejs": "Node.js",
    "php": "PHP",
    "laravel": "Laravel",
    "sql": "SQL",
    "mysql": "MySQL",
    "postgresql": "PostgreSQL",
    "mongodb": "MongoDB",
    "redis": "Redis",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "git": "Git",
    "linux": "Linux",
    "machine learning": "Machine Learning",
    "deep learning": "Deep Learning",
    "tensorflow": "TensorFlow",
    "pytorch": "PyTorch",
    "data science": "Data Science",
    "pandas": "Pandas",
    "scikit": "Scikit-learn",
    "flutter": "Flutter",
    "android": "Android",
    "ios": "iOS",
    "swift": "Swift",
    "kotlin": "Kotlin",
    "c++": "C++",
    "c#": "C#",
    ".net": ".NET",
    "aws": "AWS",
    "azure": "Azure",
    "gcp": "Google Cloud",
    "figma": "Figma",
    "rest": "REST API",
    "graphql": "GraphQL",
    "agile": "Agile/Scrum",
    "scrum": "Agile/Scrum",
    "excel": "Excel",
    "power bi": "Power BI",
    "tableau": "Tableau",
    "html": "HTML/CSS",
    "css": "HTML/CSS",
}


import os
import json
import requests

def _detect_tags(title, description):
    """Retourne les SkillTag correspondant aux compétences requises, en utilisant l'IA si disponible, sinon par mots-clés."""
    token = os.environ.get("GITHUB_TOKEN")
    available_tags = SkillTag.objects.all()
    
    if token:
        tags_list = ", ".join([t.name for t in available_tags])
        prompt = f"""
Voici une offre de stage (Titre et Description).
Identifiez quelles compétences parmi la liste des compétences disponibles sont requises pour ce stage.

Titre: {title}
Description: {description}

Compétences disponibles: {tags_list}

Instructions :
1. Retournez uniquement les compétences de la liste disponible qui sont réellement requises pour le poste.
2. Si aucune compétence disponible ne correspond, retournez une liste vide.
3. Retournez STRICTEMENT un tableau JSON de chaînes de caractères contenant les noms des compétences, sans texte additionnel (pas de markdown, pas de blabla).
Exemple de retour : ["Python", "Django", "SQL"]
"""
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "messages": [
                {"role": "system", "content": "You are a precise technical recruiter. You output raw JSON arrays of strings matching the available skills."},
                {"role": "user", "content": prompt}
            ],
            "model": "gpt-4o-mini",
            "temperature": 0.0,
            "max_tokens": 200
        }
        try:
            response = requests.post(
                "https://models.inference.ai.azure.com/chat/completions",
                headers=headers,
                json=payload,
                timeout=10
            )
            if response.status_code == 200:
                content = response.json()["choices"][0]["message"]["content"].strip()
                if content.startswith("```"):
                    content = content.strip("`").strip()
                    if content.startswith("json"):
                        content = content[4:].strip()
                names = json.loads(content)
                if isinstance(names, list):
                    matched = list(available_tags.filter(name__in=names))
                    if matched:
                        return matched
        except Exception:
            pass

    # Fallback par mots-clés
    text_lower = f"{title} {description}".lower()
    found_tag_names = set()
    for keyword, tag_name in KEYWORD_TAG_MAP.items():
        if keyword in text_lower:
            found_tag_names.add(tag_name)
    return list(available_tags.filter(name__in=found_tag_names))


def _get_or_create_linkedin_company():
    """Retourne (ou crée) le CompanyProfile et User de service pour les imports LinkedIn."""
    email = "linkedin-import@stagehub.local"
    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            "username": email,
            "first_name": "LinkedIn",
            "last_name": "Import",
            "role": User.Role.COMPANY,
            "is_active": False,  # compte non-connectab
        },
    )
    if not user.role == User.Role.COMPANY:
        user.role = User.Role.COMPANY
        user.save(update_fields=["role"])

    profile, _ = CompanyProfile.objects.get_or_create(
        user=user,
        defaults={
            "nom_entreprise": "LinkedIn — Offres Importées",
            "secteur": "Multi-secteur",
            "email_entreprise": email,
            "description_entreprise": (
                "Offres de stage importées automatiquement depuis LinkedIn "
                "via le module d'import StageHub."
            ),
            "site_web": "https://www.linkedin.com/jobs/",
        },
    )
    return profile


class Command(BaseCommand):
    help = "Importe des offres de stage PFE depuis LinkedIn via JobSpy."

    def add_arguments(self, parser):
        parser.add_argument(
            "--query",
            type=str,
            default="stage PFE informatique",
            help="Mots-clés de recherche (défaut: 'stage PFE informatique')",
        )
        parser.add_argument(
            "--location",
            type=str,
            default="Maroc",
            help="Localisation (défaut: 'Maroc')",
        )
        parser.add_argument(
            "--max-results",
            type=int,
            default=20,
            help="Nombre max d'offres à importer (défaut: 20)",
        )
        parser.add_argument(
            "--hours-old",
            type=int,
            default=168,
            help="Ancienneté max des offres en heures (défaut: 168 = 7 jours)",
        )

    def handle(self, *args, **options):
        query = options["query"]
        location = options["location"]
        total_max_results = options["max_results"]
        hours_old = options["hours_old"]

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"\nRecherche LinkedIn @ '{location}' avec mots-clés '{query}' (max {total_max_results})...\n"
            )
        )

        try:
            from jobspy import scrape_jobs
        except ImportError as exc:
            raise CommandError(
                "Bibliothèque 'python-jobspy' non installée. Exécutez : pip install python-jobspy"
            ) from exc

        self.stdout.write(f"Scraping pour: {query}...")
        try:
            jobs_df = scrape_jobs(
                site_name=["linkedin"],
                search_term=query,
                location=location,
                results_wanted=total_max_results,
                hours_old=hours_old,
                country_indeed="morocco",
                linkedin_fetch_description=True,
            )
        except Exception as e:
            self.stderr.write(f"Erreur scraping pour {query}: {e}")
            jobs_df = None

        if jobs_df is None or jobs_df.empty:
            self.stdout.write(self.style.WARNING("Aucune offre trouvée pour cette recherche."))
            return

        combined_df = jobs_df.drop_duplicates(subset=['job_url'])

        # Limiter au max_results global au cas où
        combined_df = combined_df.head(total_max_results)

        self.stdout.write(
            self.style.SUCCESS(f"[OK] {len(combined_df)} offre(s) IT recuperee(s) depuis LinkedIn.\n")
        )

        company_profile = _get_or_create_linkedin_company()
        created_count = 0
        updated_count = 0
        skipped_count = 0

        for _, row in combined_df.iterrows():
            try:
                linkedin_url = str(row.get("job_url", "") or "")
                title = str(row.get("title", "") or "Offre sans titre")[:255]
                description = str(row.get("description", "") or "")
                company_name = str(row.get("company", "") or "Entreprise LinkedIn")[:255]
                location_val = str(row.get("location", location) or location)[:255]
                domain_val = str(row.get("job_function", "") or row.get("industry", "") or "Informatique")[:255]
                date_posted = row.get("date_posted")

                # Filtrage strict : Uniquement IT et Stage/PFE
                text_to_check = (title + " " + description).lower()
                it_keywords = ["informatique", "développement", "developer", "dev", "data", "software", "ingénieur", "engineer", "cyber", "cloud", "réseau", "ia", "ai", "machine learning", "web", "mobile", "frontend", "backend", "fullstack", "système", "it", "tech"]
                pfe_keywords = ["pfe", "fin d'étude", "fin d'etude", "stage", "internship", "intern", "stagiaire"]
                
                if not any(k in text_to_check for k in it_keywords) or not any(k in text_to_check for k in pfe_keywords):
                    skipped_count += 1
                    continue

                # Dédoublonnage sur l'URL LinkedIn
                if linkedin_url:
                    existing = StageOffer.objects.filter(linkedin_url=linkedin_url).first()
                    if existing:
                        skipped_count += 1
                        continue

                # Enrichissement de la description avec le nom de l'entreprise
                if company_name and company_name not in description[:50]:
                    full_description = f"[{company_name}]\n\n{description}"
                else:
                    full_description = description

                # Détection automatique des tags
                tags = _detect_tags(title, full_description)

                # Création de l'offre
                offer = StageOffer.objects.create(
                    company_profile=company_profile,
                    title=title[:255],
                    description=full_description or "Voir le détail sur LinkedIn.",
                    domain=domain_val[:255],
                    location=location_val[:255],
                    duration="Non précisée",
                    status=StageOffer.Status.ACTIVE,
                    source=StageOffer.Source.LINKEDIN,
                    linkedin_url=linkedin_url,
                )
                if tags:
                    offer.required_tags.set(tags)

                created_count += 1
                self.stdout.write(f"  [+] Creee : {title[:60]}...")

            except Exception as exc:
                self.stderr.write(self.style.ERROR(f"  [!] Erreur sur une ligne : {exc}"))
                continue

        self.stdout.write(
            self.style.SUCCESS(
                f"\n[RESUME] {created_count} creee(s), "
                f"{updated_count} mise(s) a jour, {skipped_count} doublon(s) ignore(s)."
            )
        )
