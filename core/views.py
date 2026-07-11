from collections import OrderedDict
from datetime import timedelta
from functools import wraps
from io import StringIO

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.management import call_command
from django.db.models import Count, Q
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import (
    ApplicationForm,
    CompanyProfileForm,
    EmailLoginForm,
    LinkedInImportForm,
    RegisterForm,
    StageOfferForm,
    StudentProfileForm,
)
from .models import AdminActionLog, Application, SkillTag, StageOffer, User
from .services import attach_match_details, attach_match_scores, match_detail


def role_required(role):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if request.user.role != role:
                messages.error(request, "Acces non autorise pour ce role.")
                return redirect("home")
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


def dashboard_for_user(user):
    if user.role == User.Role.STUDENT:
        return "student_dashboard"
    if user.role == User.Role.COMPANY:
        return "company_dashboard"
    if user.role == User.Role.ADMIN:
        return "admin_dashboard"
    return "home"


def log_admin_action(request, action, target_type, target_id=None, description=""):
    AdminActionLog.objects.create(
        user=request.user if request.user.is_authenticated else None,
        action=action,
        target_type=target_type,
        target_id=target_id,
        description=description,
        ip_address=request.META.get("REMOTE_ADDR") or None,
    )


def home(request):
    recent_offers = list(
        StageOffer.objects.select_related("company_profile")
        .filter(status=StageOffer.Status.ACTIVE)
        .order_by("-created_at")[:2]
    )
    return render(
        request,
        "home.html",
        {
            "users_count": User.objects.count(),
            "offers_count": StageOffer.objects.filter(status=StageOffer.Status.ACTIVE).count(),
            "applications_count": Application.objects.count(),
            "recent_offers": recent_offers,
        },
    )


def faq(request):
    return render(request, "pages/faq.html")


def help_page(request):
    return render(request, "pages/help.html")


def register_view(request):
    if request.user.is_authenticated:
        return redirect(dashboard_for_user(request.user))

    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Compte cree avec succes.")
        return redirect(dashboard_for_user(user))

    return render(request, "auth/register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect(dashboard_for_user(request.user))

    form = EmailLoginForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        login(request, user)
        return redirect(dashboard_for_user(user))

    return render(request, "auth/login.html", {"form": form})


@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, "Vous etes deconnecte.")
    return redirect("home")


def offres_index(request):
    keyword = request.GET.get("q", "").strip()
    domain = request.GET.get("domain", "").strip()
    location = request.GET.get("location", "").strip()
    source_filter = request.GET.get("source", "").strip()

    offers = StageOffer.objects.select_related("company_profile").prefetch_related(
        "required_tags"
    ).filter(status=StageOffer.Status.ACTIVE)

    if keyword:
        offers = offers.filter(Q(title__icontains=keyword) | Q(description__icontains=keyword))
    if domain:
        offers = offers.filter(domain__icontains=domain)
    if location:
        offers = offers.filter(location__icontains=location)
    if source_filter in ("local", "linkedin"):
        offers = offers.filter(source=source_filter)

    offer_list = list(offers)
    offer_list.sort(key=lambda offer: offer.created_at, reverse=True)

    return render(
        request,
        "offres/index.html",
        {
            "offers": offer_list,
            "filters": {"q": keyword, "domain": domain, "location": location, "source": source_filter},
        },
    )


def offres_show(request, pk):
    offer = get_object_or_404(
        StageOffer.objects.select_related("company_profile").prefetch_related("required_tags"),
        pk=pk,
    )
    student_profile = getattr(request.user, "student_profile", None) if request.user.is_authenticated else None

    already_applied = False
    if student_profile:
        already_applied = Application.objects.filter(
            stage_offer=offer,
            student_profile=student_profile,
        ).exists()

    return render(
        request,
        "offres/show.html",
        {
            "offer": offer,
            "application_form": ApplicationForm(),
            "already_applied": already_applied,
        },
    )


@role_required(User.Role.STUDENT)
def student_dashboard(request):
    profile = request.user.student_profile
    applications = profile.applications.select_related("stage_offer", "stage_offer__company_profile")
    active_offers = StageOffer.objects.select_related("company_profile").prefetch_related("required_tags").filter(status=StageOffer.Status.ACTIVE)
    
    internal_offers = list(active_offers.filter(source=StageOffer.Source.LOCAL).order_by("-created_at")[:10])
    linkedin_offers = list(active_offers.filter(source=StageOffer.Source.LINKEDIN).order_by("-created_at")[:10])
    
    from .services import match_offer_for_student
    for offer in internal_offers:
        offer.ai_score = match_offer_for_student(offer, profile)
    internal_offers.sort(key=lambda offer: (offer.ai_score, offer.created_at), reverse=True)

    for offer in linkedin_offers:
        offer.ai_score = match_offer_for_student(offer, profile)
    linkedin_offers.sort(key=lambda offer: (offer.ai_score, offer.created_at), reverse=True)

    return render(
        request,
        "student/dashboard.html",
        {
            "stats": {
                "total": applications.count(),
                "pending": applications.filter(status=Application.Status.PENDING).count(),
                "accepted": applications.filter(status=Application.Status.ACCEPTED).count(),
            },
            "recent_applications": applications[:3],
            "internal_offers": internal_offers[:4],
            "linkedin_offers": linkedin_offers[:4],
        },
    )


@role_required(User.Role.STUDENT)
def student_profile_edit(request):
    form = StudentProfileForm(
        request.user,
        request.POST or None,
        request.FILES or None,
    )
    if request.method == "POST" and form.is_valid():
        profile = form.save()
        if request.FILES.get("cv_profile"):
            # Auto-extract skills using AI
            from .services import extract_text_from_file, extract_skills_from_cv
            cv_file = request.FILES["cv_profile"]
            cv_text = extract_text_from_file(cv_file)
            all_tags = list(SkillTag.objects.values_list("name", flat=True))
            extracted_names = extract_skills_from_cv(cv_text, all_tags)
            
            matched_tags = SkillTag.objects.filter(name__in=extracted_names)
            profile.skill_tags.set(matched_tags)
            
            messages.success(request, f"Profil mis à jour et {matched_tags.count()} compétence(s) extraite(s) automatiquement de votre CV.")
        else:
            messages.success(request, "Profil mis à jour avec succès.")
        return redirect("student_profile_edit")

    return render(request, "student/profile_edit.html", {
        "form": form,
    })


@role_required(User.Role.COMPANY)
def company_dashboard(request):
    profile = request.user.company_profile
    offers = profile.stage_offers.all()
    applications = Application.objects.select_related("stage_offer", "student_profile", "student_profile__user").filter(
        stage_offer__company_profile=profile
    )

    months = []
    application_counts = []
    today = timezone.localdate()
    for offset in range(5, -1, -1):
        month_index = today.month - offset
        year = today.year + ((month_index - 1) // 12)
        month = ((month_index - 1) % 12) + 1
        months.append(f"{month:02d}/{year}")
        application_counts.append(applications.filter(applied_at__year=year, applied_at__month=month).count())

    return render(
        request,
        "company/dashboard.html",
        {
            "offers_count": offers.count(),
            "applications_count": applications.count(),
            "recent_applications": applications[:3],
            "months": months,
            "application_counts": application_counts,
        },
    )


@role_required(User.Role.COMPANY)
def company_profile_edit(request):
    form = CompanyProfileForm(
        request.user,
        request.POST or None,
        request.FILES or None,
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profil entreprise mis a jour avec succes.")
        return redirect("company_profile_edit")
    return render(request, "company/profile_edit.html", {"form": form})


@role_required(User.Role.COMPANY)
def offres_create(request):
    form = StageOfferForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        offer = form.save(commit=False)
        offer.company_profile = request.user.company_profile
        offer.save()
        form.save_m2m()  # Sauvegarde des required_tags (ManyToMany)
        messages.success(request, "Offre publiee avec succes.")
        return redirect("offres_company")

    # IDs des tags sélectionnés (depuis POST si erreur de formulaire)
    if request.method == "POST":
        selected_tag_ids = set(int(x) for x in request.POST.getlist("required_tags") if x.isdigit())
    else:
        selected_tag_ids = set()

    tags_by_category = {}
    for tag in SkillTag.objects.all().order_by("category", "name"):
        tags_by_category.setdefault(tag.get_category_display(), []).append(tag)

    return render(request, "offres/form.html", {
        "form": form,
        "title": "Publier une offre",
        "tags_by_category": tags_by_category,
        "selected_tag_ids": selected_tag_ids,
    })


@role_required(User.Role.COMPANY)
def offres_company(request):
    offers = (
        request.user.company_profile.stage_offers.annotate(applications_count=Count("applications"))
        .order_by("-created_at")
    )
    return render(
        request,
        "offres/company_index.html",
        {
            "offers": offers,
            "stats": {
                "total": offers.count(),
                "active": offers.filter(status=StageOffer.Status.ACTIVE).count(),
            },
        },
    )


@role_required(User.Role.COMPANY)
def offres_edit(request, pk):
    offer = get_object_or_404(StageOffer, pk=pk, company_profile=request.user.company_profile)
    form = StageOfferForm(request.POST or None, instance=offer)
    if request.method == "POST" and form.is_valid():
        form.save()
        log_admin_action(
            request,
            "update",
            "stage_offer",
            offer.pk,
            f"Mise a jour de l'offre: {offer.title}",
        )
        messages.success(request, "Offre mise a jour avec succes.")
        return redirect("offres_company")

    # IDs des tags sélectionnés : depuis POST (erreur form) ou depuis l'instance
    if request.method == "POST":
        selected_tag_ids = set(int(x) for x in request.POST.getlist("required_tags") if x.isdigit())
    else:
        selected_tag_ids = set(offer.required_tags.values_list("id", flat=True))

    tags_by_category = {}
    for tag in SkillTag.objects.all().order_by("category", "name"):
        tags_by_category.setdefault(tag.get_category_display(), []).append(tag)

    return render(request, "offres/form.html", {
        "form": form,
        "title": "Modifier une offre",
        "tags_by_category": tags_by_category,
        "selected_tag_ids": selected_tag_ids,
    })


@require_POST
@role_required(User.Role.COMPANY)
def offres_destroy(request, pk):
    offer = get_object_or_404(StageOffer, pk=pk, company_profile=request.user.company_profile)
    title = offer.title
    offer.delete()
    log_admin_action(request, "delete", "stage_offer", pk, f"Suppression de l'offre: {title}")
    messages.success(request, "Offre supprimee avec succes.")
    return redirect("offres_company")


@require_POST
@role_required(User.Role.STUDENT)
def applications_store(request, pk):
    offer = get_object_or_404(StageOffer, pk=pk, status=StageOffer.Status.ACTIVE)
    profile = request.user.student_profile
    if Application.objects.filter(stage_offer=offer, student_profile=profile).exists():
        messages.error(request, "Vous avez deja postule a cette offre.")
        return redirect("offres_show", pk=pk)

    form = ApplicationForm(request.POST, request.FILES)
    if form.is_valid():
        application = form.save(commit=False)
        application.stage_offer = offer
        application.student_profile = profile
        application.cv_original_name = request.FILES["cv"].name
        application.cover_letter_original_name = request.FILES["cover_letter"].name
        
        # Analyse IA du CV
        from .services import extract_text_from_file, evaluate_cv_for_offer, match_offer_for_student
        cv_file = request.FILES["cv"]
        cv_text = extract_text_from_file(cv_file)
        offer_tags = ", ".join([t.name for t in offer.required_tags.all()])
        evaluation = evaluate_cv_for_offer(cv_text, offer.title, offer.description, offer_tags)
        
        # Le score de matching est maintenant strictement mathématique (unifié)
        application.ai_match_score = match_offer_for_student(offer, profile)
        application.ai_match_reasoning = evaluation.get("reasoning", "")
        
        application.save()
        messages.success(request, "Candidature envoyee avec succes.")
        return redirect("applications_my")

    messages.error(request, "Veuillez joindre un CV et une lettre de motivation valides.")
    return render(
        request,
        "offres/show.html",
        {"offer": offer, "application_form": form, "already_applied": False},
    )


@role_required(User.Role.STUDENT)
def applications_my(request):
    applications = request.user.student_profile.applications.select_related(
        "stage_offer",
        "stage_offer__company_profile",
    )
    return render(
        request,
        "applications/my.html",
        {
            "applications": applications,
            "stats": {
                "total": applications.count(),
                "pending": applications.filter(status=Application.Status.PENDING).count(),
                "accepted": applications.filter(status=Application.Status.ACCEPTED).count(),
            },
        },
    )


@role_required(User.Role.COMPANY)
def applications_company(request):
    applications = Application.objects.select_related(
        "stage_offer",
        "student_profile",
        "student_profile__user",
    ).prefetch_related(
        "stage_offer__required_tags",
        "student_profile__skill_tags",
    ).filter(stage_offer__company_profile=request.user.company_profile)

    # Mapping du score IA statique calculé au moment de la candidature
    for application in applications:
        application.match_score = application.ai_match_score
        application.match_reasoning = application.ai_match_reasoning
        
        offer_tags = set(application.stage_offer.required_tags.all())
        student_tags = set(application.student_profile.skill_tags.all())
        application.matched_tags = list(offer_tags.intersection(student_tags))

    grouped = OrderedDict()
    for application in applications:
        grouped.setdefault(application.stage_offer.title, []).append(application)

    # Trier les candidats par score décroissant dans chaque offre
    for title in grouped:
        grouped[title].sort(key=lambda a: a.match_score, reverse=True)

    return render(
        request,
        "applications/company.html",
        {
            "grouped_applications": grouped.items(),
            "stats": {
                "total": applications.count(),
                "pending": applications.filter(status=Application.Status.PENDING).count(),
                "accepted": applications.filter(status=Application.Status.ACCEPTED).count(),
                "rejected": applications.filter(status=Application.Status.REJECTED).count(),
            },
        },
    )


def _company_application(request, pk):
    return get_object_or_404(
        Application.objects.select_related("stage_offer"),
        pk=pk,
        stage_offer__company_profile=request.user.company_profile,
    )


@require_POST
@role_required(User.Role.COMPANY)
def applications_accept(request, pk):
    application = _company_application(request, pk)
    application.status = Application.Status.ACCEPTED
    application.save(update_fields=["status", "updated_at"])
    messages.success(request, "Candidature acceptee.")
    return redirect("applications_company")


@require_POST
@role_required(User.Role.COMPANY)
def applications_reject(request, pk):
    application = _company_application(request, pk)
    application.status = Application.Status.REJECTED
    application.save(update_fields=["status", "updated_at"])
    messages.success(request, "Candidature refusee.")
    return redirect("applications_company")


@role_required(User.Role.COMPANY)
def applications_download_cv(request, pk):
    application = _company_application(request, pk)
    return FileResponse(
        application.cv.open("rb"),
        as_attachment=True,
        filename=application.cv_original_name or "cv-candidature",
    )


@role_required(User.Role.COMPANY)
def applications_download_cover_letter(request, pk):
    application = _company_application(request, pk)
    return FileResponse(
        application.cover_letter.open("rb"),
        as_attachment=True,
        filename=application.cover_letter_original_name or "lettre-motivation",
    )


@role_required(User.Role.ADMIN)
def admin_dashboard(request):
    activity_data = []
    today = timezone.localdate()
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        activity_data.append(
            {
                "day": day.strftime("%d/%m"),
                "count": StageOffer.objects.filter(created_at__date=day).count(),
            }
        )

    return render(
        request,
        "admin/dashboard.html",
        {
            "users_count": User.objects.count(),
            "offers_count": StageOffer.objects.count(),
            "applications_count": Application.objects.count(),
            "students_count": User.objects.filter(role=User.Role.STUDENT).count(),
            "companies_count": User.objects.filter(role=User.Role.COMPANY).count(),
            "activity_data": activity_data,
            "recent_logs": AdminActionLog.objects.select_related("user")[:8],
            "linkedin_offers_count": StageOffer.objects.filter(source=StageOffer.Source.LINKEDIN).count(),
        },
    )


@role_required(User.Role.ADMIN)
def admin_users_index(request):
    users = User.objects.all().order_by("-date_joined")
    q = request.GET.get("q", "").strip()
    role = request.GET.get("role", "").strip()
    if q:
        users = users.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(email__icontains=q))
    if role:
        users = users.filter(role=role)
    return render(request, "admin/users_index.html", {"users": users, "q": q, "role": role})


@require_POST
@role_required(User.Role.ADMIN)
def admin_users_destroy(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user.pk == request.user.pk:
        messages.error(request, "Suppression de votre propre compte administrateur interdite.")
        return redirect("admin_users_index")
    primary_admin = User.objects.filter(role=User.Role.ADMIN).order_by("pk").first()
    if primary_admin and user.pk == primary_admin.pk:
        messages.error(request, "Suppression du compte administrateur principal interdite.")
        return redirect("admin_users_index")
    name = user.get_full_name() or user.email
    user.delete()
    log_admin_action(request, "delete", "user", pk, f"Suppression du compte utilisateur: {name}")
    messages.success(request, "Utilisateur supprime avec succes.")
    return redirect("admin_users_index")


@role_required(User.Role.ADMIN)
def admin_offers_index(request):
    offers = StageOffer.objects.select_related("company_profile").annotate(applications_count=Count("applications"))
    q = request.GET.get("q", "").strip()
    domain = request.GET.get("domain", "").strip()
    location = request.GET.get("location", "").strip()
    if q:
        offers = offers.filter(title__icontains=q)
    if domain:
        offers = offers.filter(domain__icontains=domain)
    if location:
        offers = offers.filter(location__icontains=location)
    return render(
        request,
        "admin/offers_index.html",
        {"offers": offers, "filters": {"q": q, "domain": domain, "location": location}},
    )


@require_POST
@role_required(User.Role.ADMIN)
def admin_offers_destroy(request, pk):
    offer = get_object_or_404(StageOffer, pk=pk)
    title = offer.title
    offer.delete()
    log_admin_action(request, "delete", "stage_offer", pk, f"Suppression de l'offre: {title}")
    messages.success(request, "Offre supprimee avec succes.")
    return redirect("admin_offers_index")


@role_required(User.Role.ADMIN)
def admin_import_linkedin(request):
    """Vue admin pour déclencher l'import LinkedIn depuis l'interface web."""
    form = LinkedInImportForm(request.POST or None)
    output = None
    error = None

    if request.method == "POST" and form.is_valid():
        query = form.cleaned_data["query"]
        location = form.cleaned_data["location"]
        max_results = form.cleaned_data["max_results"]
        hours_old = form.cleaned_data["hours_old"]

        try:
            buf = StringIO()
            call_command(
                "import_linkedin_jobs",
                query=query,
                location=location,
                max_results=max_results,
                hours_old=hours_old,
                stdout=buf,
            )
            output = buf.getvalue()
            log_admin_action(
                request,
                "import",
                "linkedin_jobs",
                description=f"Import LinkedIn: '{query}' @ '{location}' — {max_results} max",
            )
            messages.success(request, "Import LinkedIn terminé avec succès.")
        except Exception as exc:
            error = str(exc)
            messages.error(request, f"Erreur lors de l'import : {error}")

    return render(request, "admin/import_linkedin.html", {
        "form": form,
        "output": output,
        "error": error,
    })


def api_offers(request):
    offers = StageOffer.objects.select_related("company_profile").filter(status=StageOffer.Status.ACTIVE)
    return JsonResponse(
        [
            {
                "id": offer.pk,
                "title": offer.title,
                "description": offer.description,
                "domain": offer.domain,
                "location": offer.location,
                "duration": offer.duration,
                "closing_date": offer.closing_date.isoformat() if offer.closing_date else None,
                "company": offer.company_profile.nom_entreprise,
                "source": offer.source,
                "linkedin_url": offer.linkedin_url,
            }
            for offer in offers
        ],
        safe=False,
    )


def api_offer_detail(request, pk):
    offer = get_object_or_404(StageOffer.objects.select_related("company_profile"), pk=pk)
    return JsonResponse(
        {
            "id": offer.pk,
            "title": offer.title,
            "description": offer.description,
            "domain": offer.domain,
            "location": offer.location,
            "duration": offer.duration,
            "closing_date": offer.closing_date.isoformat() if offer.closing_date else None,
            "status": offer.status,
            "company": offer.company_profile.nom_entreprise,
            "source": offer.source,
            "linkedin_url": offer.linkedin_url,
        }
    )


def api_match_score(request, pk, student_pk):
    """API JSON : retourne le score de matching détaillé pour un étudiant et une offre."""
    from .models import StudentProfile
    offer = get_object_or_404(StageOffer.objects.prefetch_related("required_tags"), pk=pk)
    student_profile = get_object_or_404(StudentProfile.objects.prefetch_related("skill_tags"), pk=student_pk)
    detail = match_detail(offer, student_profile)
    return JsonResponse({
        "offer_id": pk,
        "student_id": student_pk,
        "score_total": detail["total"],
        "score_tags": detail["tag_score"],
        "score_text": detail["text_score"],
        "matched_tags": [t.name for t in detail["matched_tags"]],
        "missing_tags": [t.name for t in detail["missing_tags"]],
    })
