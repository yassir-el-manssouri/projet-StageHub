# StageHub Django

Migration Django de l'application Laravel `G_Offre_Stage_Laravel`.

## Stack

| Categorie | Outil / Technologie | Role |
| --- | --- | --- |
| Langage back-end | Python 3.14 | Logique metier, moteur de matching IA local, webservices JSON |
| Framework web | Django | Architecture MVT, ORM, authentification, routage, admin integre |
| Base de donnees | SQLite en dev / MySQL en production | Utilisateurs, offres, candidatures, workflows |
| Front-end | HTML5, CSS3, Bootstrap 5 | Interfaces responsives par role |

## Lancer en local

```powershell
cd C:\Users\yassi\Documents\Codex\2026-05-29\files-mentioned-by-the-user-g\stagehub_django
python manage.py migrate
python manage.py seed_demo
python manage.py createsuperuser
python manage.py runserver 127.0.0.1:8000
```

Les emails de reinitialisation du mot de passe sont affiches dans le terminal en developpement.

La commande `seed_demo` cree trois comptes avec le mot de passe `password123` :

- `admin@example.com`
- `etudiant@example.com`
- `entreprise@example.com`

## MySQL production

Installez le connecteur MySQL puis activez les variables de `.env.example` :

```powershell
pip install mysqlclient
$env:DB_ENGINE="mysql"
$env:DB_NAME="stagehub"
$env:DB_USER="stagehub_user"
$env:DB_PASSWORD="change-me"
python manage.py migrate
```
