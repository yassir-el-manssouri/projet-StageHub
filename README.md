<div align="center">

# 🎓 StageHub — Plateforme Intelligente de Gestion des Stages & PFE

[![Django](https://img.shields.io/badge/Django-4.2_LTS-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

Une plateforme web complète dédiée à la gestion, au suivi et à l'agrégation automatisée d'offres de stages (PFE, PFA, pré-embauche) pour les étudiants et établissements d'enseignement supérieur.

[Fonctionnalités](#-fonctionnalités) • [Stack Technique](#%EF%B8%8F-stack-technique) • [Installation](#-installation--démarrage)

</div>

---

## 🌟 Fonctionnalités

- 🎯 **Agrégation Intelligente d'Offres :** Scraping et collecte automatisée d'offres de stages via `python-jobspy` (LinkedIn, Indeed, Glassdoor).
- 👨‍🎓 **Espace Étudiants :** Profil avec CV, recherche avancée par mot-clé, ville et technologies, suivi en direct de l'état des candidatures.
- 🏢 **Espace Entreprises & Recruteurs :** Publication d'offres, tri des candidatures et gestion des entretiens.
- 📊 **Tableau de Bord Administratif :** Validation des conventions de stage, affectation des encadrants académiques et suivi des soutenances.
- 📑 **Génération de Documents :** Automatisation des conventions, attestations et fiches d'évaluation de stage.

---

## 🛠️ Stack Technique

- **Backend :** [Django 4.2 LTS](https://www.djangoproject.com/) (Python)
- **Scraping & Aggregation :** `python-jobspy`
- **Base de Données :** SQLite (développement) / PostgreSQL (production)
- **Frontend :** HTML5, CSS3, JavaScript, Django Templates & Bootstrap
- **Authentification :** Système de permissions et rôles Django (Étudiant, Entreprise, Administrateur)

---

## 📂 Structure du Répertoire

```bash
projet-StageHub/
├── config/              # Configuration globale du projet Django (settings, urls, wsgi)
├── core/                # Application principale (modèles, vues, formulaires)
│   ├── models.py        # Modèles (Offres, Candidatures, Profils, Entreprises)
│   ├── views.py         # Logique métier et contrôleurs
│   └── urls.py          # Routage des pages
├── static/              # Fichiers CSS, JS, images et logos
├── templates/           # Vues HTML Django Templates
├── .env.example         # Variables d'environnement (template)
├── manage.py            # Script d'administration Django
└── requirements.txt     # Dépendances Python
```

---

## 🚀 Installation & Démarrage

### 1. Cloner le projet
```bash
git clone https://github.com/yassir-el-manssouri/projet-StageHub.git
cd projet-StageHub
```

### 2. Créer et activer un environnement virtuel
```bash
python -m venv venv
# Sur Windows :
venv\Scripts\activate
# Sur Linux/Mac :
source venv/bin/activate
```

### 3. Installer les dépendances
```bash
pip install -r requirements.txt
```

### 4. Appliquer les migrations de base de données
```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Créer un super-utilisateur (Admin)
```bash
python manage.py createsuperuser
```

### 6. Lancer le serveur local
```bash
python manage.py runserver
```
Rendez-vous sur `http://127.0.0.1:8000` (Administration accessible sur `http://127.0.0.1:8000/admin`).

---

## 👤 Auteur

- **Yassir EL MANSSOURI** - [@yassir-el-manssouri](https://github.com/yassir-el-manssouri) | [LinkedIn](https://www.linkedin.com/in/yassir-el-manssouri/)
- Étudiant / Ingénieur à l'École Marocaine des Sciences de l'Ingénieur (EMSI).

