import re
import os
import json
import requests
import pypdf


TOKEN_RE = re.compile(r"[a-zA-Z0-9+#.-]+")


def _tokens(value):
    return {item.lower() for item in TOKEN_RE.findall(value or "") if len(item) > 2}

def extract_skills_from_cv(cv_text, available_tags):
    if not cv_text or not available_tags:
        return []
    
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        return []

    tags_str = ", ".join(available_tags)
    prompt = f"""
Vous êtes un expert en analyse de CV.
Voici le texte d'un CV:
{cv_text}

Voici une liste de compétences techniques possibles:
{tags_str}

Extrayez du CV les compétences qui sont EXACTEMENT dans cette liste (casse ignorée, mais même mot).
Retournez STRICTEMENT un tableau JSON contenant uniquement les noms des compétences trouvées, sans aucun texte supplémentaire.
Exemple: ["Python", "Django", "SQL"]
"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "messages": [
            {"role": "system", "content": "You output only a valid JSON array of strings."},
            {"role": "user", "content": prompt}
        ],
        "model": "gpt-4o-mini",
        "temperature": 0.0,
        "max_tokens": 500
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
            data = json.loads(content)
            if isinstance(data, list):
                return data
    except Exception as e:
        print(f"Erreur extract_skills_from_cv: {e}")
    return []


def match_offer_for_student(offer, student_profile):
    """
    Retourne le score de matching global (0-100) en utilisant la logique détaillée.
    """
    return match_detail(offer, student_profile)["total"]


def match_detail(offer, student_profile):
    """
    Retourne un dictionnaire détaillé du score de matching pour un affichage
    riche côté template (barre de progression, détail par composante).
    """
    if not student_profile:
        return {"total": 0, "tag_score": 0, "text_score": 0, "matched_tags": [], "missing_tags": [], "reasoning": None}


    student_tag_ids = set(
        student_profile.skill_tags.values_list("id", flat=True)
    ) if hasattr(student_profile, "skill_tags") else set()

    offer_tag_ids = set(
        offer.required_tags.values_list("id", flat=True)
    ) if hasattr(offer, "required_tags") else set()

    matched_tags = list(
        offer.required_tags.filter(id__in=student_tag_ids)
    ) if offer_tag_ids else []
    missing_tags = list(
        offer.required_tags.exclude(id__in=student_tag_ids)
    ) if offer_tag_ids else []

    if offer_tag_ids:
        # Moins exigeant : on cap le nombre de tags requis à 3 pour avoir 100% du score tag
        tag_coverage = min(1.0, len(matched_tags) / max(1, min(len(offer_tag_ids), 3)))
        tag_score_pct = round(tag_coverage * 60)
    else:
        # S'il n'y a pas de tags requis, on donne les points par défaut
        tag_score_pct = 60

    student_tokens = _tokens(
        " ".join([student_profile.specialite, student_profile.competences, student_profile.universite])
    )
    offer_tokens = _tokens(" ".join([offer.title, offer.description, offer.domain]))
    if student_tokens and offer_tokens:
        text_overlap = len(student_tokens & offer_tokens)
        text_coverage = text_overlap / max(len(offer_tokens), 1)
        # On donne un bonus de base de 0.2 et des poids plus généreux
        raw_text = min(1.0, (text_overlap * 0.25) + (text_coverage * 0.5) + 0.2)
    else:
        raw_text = 0.2
    text_score_pct = round(raw_text * 40)



    return {
        "total": min(100, tag_score_pct + text_score_pct),
        "tag_score": tag_score_pct,
        "text_score": text_score_pct,
        "matched_tags": matched_tags,
        "missing_tags": missing_tags,
        "reasoning": None,
    }

def extract_text_from_file(file_obj):
    """Extrait le texte brut d'un fichier CV (supporte principalement le PDF)."""
    text = ""
    try:
        # Assurer que le curseur est au début
        file_obj.seek(0)
        reader = pypdf.PdfReader(file_obj)
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
    except Exception as e:
        print(f"Erreur d'extraction de texte PDF: {e}")
    finally:
        # Remettre le curseur au début pour que Django puisse sauvegarder le fichier correctement
        file_obj.seek(0)
    return text.strip()

def evaluate_cv_for_offer(cv_text, offer_title, offer_description, offer_tags=""):
    """
    Envoie le texte du CV et les exigences de l'offre à l'API GitHub Models 
    pour calculer le score de matching au moment de la candidature.
    """
    if not cv_text:
        return {"score": 0, "reasoning": "Impossible de lire le contenu du CV ou CV vide."}
        
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        # Fallback si pas de token
        return {"score": 50, "reasoning": "Matching IA désactivé (pas de token configuré)."}
        
    prompt = f"""
Vous êtes un recruteur expert en informatique et IT.
Votre mission est d'évaluer l'adéquation entre le CV d'un candidat et une offre de stage.

-- OFFRE DE STAGE --
Titre : {offer_title}
Compétences clés attendues : {offer_tags}
Description :
{offer_description}

-- CV DU CANDIDAT (Texte extrait) --
{cv_text}

Instructions :
1. Évaluez le CV du candidat par rapport aux exigences du stage.
2. Attribuez un score de 0 à 100 basé sur la correspondance des compétences et du profil.
3. Retournez STRICTEMENT un objet JSON valide.
Exemple de format :
{{
  "score": 85,
  "reasoning": "Le candidat possède une forte expérience en Python et Django, ce qui correspond parfaitement aux attentes de l'offre. Cependant, il manque des bases en cloud."
}}
"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "messages": [
            {"role": "system", "content": "You are an expert technical recruiter. You output raw JSON matching the requested structure."},
            {"role": "user", "content": prompt}
        ],
        "model": "gpt-4o-mini",
        "temperature": 0.0,
        "max_tokens": 300
    }
    
    try:
        response = requests.post(
            "https://models.inference.ai.azure.com/chat/completions",
            headers=headers,
            json=payload,
            timeout=15
        )
        if response.status_code == 200:
            content = response.json()["choices"][0]["message"]["content"].strip()
            if content.startswith("```"):
                content = content.strip("`").strip()
                if content.startswith("json"):
                    content = content[4:].strip()
            data = json.loads(content)
            score = min(100, max(0, int(data.get("score", 0))))
            return {"score": score, "reasoning": data.get("reasoning", "")}
    except Exception as e:
        print(f"Erreur appel API IA: {e}")
        pass
        
    return {"score": 0, "reasoning": "Le moteur de calcul IA a rencontré une erreur technique."}


def attach_match_scores(offers, student_profile):
    for offer in offers:
        offer.ai_score = match_offer_for_student(offer, student_profile)
    return offers


def attach_match_details(offers, student_profile):
    """Attache un dict 'match_detail' à chaque offre pour un affichage riche."""
    for offer in offers:
        offer.ai_score = match_offer_for_student(offer, student_profile)
        offer.match_detail = match_detail(offer, student_profile)
    return offers
