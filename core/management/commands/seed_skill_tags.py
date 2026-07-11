"""
Commande Django : seed_skill_tags
Peuple la table SkillTag avec une liste prédéfinie de compétences techniques.

Usage :
    python manage.py seed_skill_tags
"""
from django.core.management.base import BaseCommand

from core.models import SkillTag

SKILLS = [
    # Backend
    ("Python", "backend", "bi-filetype-py"),
    ("Django", "backend", "bi-layers"),
    ("Flask", "backend", "bi-cup-hot"),
    ("FastAPI", "backend", "bi-lightning"),
    ("Java", "backend", "bi-filetype-java"),
    ("Spring Boot", "backend", "bi-gear"),
    ("PHP", "backend", "bi-filetype-php"),
    ("Laravel", "backend", "bi-box"),
    ("Node.js", "backend", "bi-filetype-js"),
    ("C#", "backend", "bi-hash"),
    (".NET", "backend", "bi-microsoft"),
    ("C++", "backend", "bi-cpu"),
    ("REST API", "backend", "bi-arrow-left-right"),
    ("GraphQL", "backend", "bi-diagram-3"),
    # Frontend
    ("JavaScript", "frontend", "bi-filetype-js"),
    ("TypeScript", "frontend", "bi-filetype-tsx"),
    ("React", "frontend", "bi-grid-3x3-gap"),
    ("Vue.js", "frontend", "bi-layout-text-sidebar"),
    ("Angular", "frontend", "bi-triangle"),
    ("HTML/CSS", "frontend", "bi-filetype-html"),
    # Data / IA
    ("Python", "data", "bi-filetype-py"),
    ("Machine Learning", "data", "bi-robot"),
    ("Deep Learning", "data", "bi-cpu"),
    ("TensorFlow", "data", "bi-bezier2"),
    ("PyTorch", "data", "bi-fire"),
    ("Data Science", "data", "bi-bar-chart-line"),
    ("Pandas", "data", "bi-table"),
    ("Scikit-learn", "data", "bi-graph-up"),
    ("SQL", "data", "bi-database"),
    ("Power BI", "data", "bi-pie-chart"),
    ("Tableau", "data", "bi-grid"),
    ("Excel", "data", "bi-file-earmark-spreadsheet"),
    # DevOps / Cloud
    ("Docker", "devops", "bi-box-seam"),
    ("Kubernetes", "devops", "bi-diagram-2"),
    ("Git", "devops", "bi-git"),
    ("Linux", "devops", "bi-terminal"),
    ("AWS", "devops", "bi-cloud"),
    ("Azure", "devops", "bi-cloud-fill"),
    ("Google Cloud", "devops", "bi-cloud-sun"),
    ("CI/CD", "devops", "bi-arrow-repeat"),
    # Base de données
    ("MySQL", "backend", "bi-database"),
    ("PostgreSQL", "backend", "bi-database-fill"),
    ("MongoDB", "backend", "bi-leaf"),
    ("Redis", "backend", "bi-lightning-fill"),
    # Mobile
    ("Flutter", "mobile", "bi-phone"),
    ("Android", "mobile", "bi-android"),
    ("iOS", "mobile", "bi-apple"),
    ("React Native", "mobile", "bi-phone-fill"),
    ("Swift", "mobile", "bi-suit-spade"),
    ("Kotlin", "mobile", "bi-braces"),
    # Design / UX
    ("Figma", "design", "bi-pen"),
    ("Adobe XD", "design", "bi-vector-pen"),
    # Autre
    ("Agile/Scrum", "other", "bi-people"),
    ("Merise", "other", "bi-diagram-3-fill"),
    ("UML", "other", "bi-boxes"),
    ("Cybersécurité", "other", "bi-shield-lock"),
    ("Réseaux", "other", "bi-router"),
    ("SAP", "other", "bi-building"),
]


class Command(BaseCommand):
    help = "Crée les SkillTags prédéfinis dans la base de données."

    def handle(self, *args, **options):
        created = 0
        skipped = 0
        seen_names = set()

        for name, category, icon in SKILLS:
            if name in seen_names:
                continue
            seen_names.add(name)
            _, was_created = SkillTag.objects.get_or_create(
                name=name,
                defaults={"category": category, "icon": icon},
            )
            if was_created:
                created += 1
                self.stdout.write(f"  [OK] Cree : {name} [{category}]")
            else:
                skipped += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\n[DONE] {created} tag(s) cree(s), {skipped} deja existant(s)."
            )
        )
