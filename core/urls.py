from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views


urlpatterns = [
    path("", views.home, name="home"),
    path("faq/", views.faq, name="faq"),
    path("aide/", views.help_page, name="help"),
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("mot-de-passe-oublie/", auth_views.PasswordResetView.as_view(
        template_name="registration/password_reset_form.html",
        email_template_name="registration/password_reset_email.txt",
        success_url=reverse_lazy("password_reset_done"),
    ), name="password_reset"),
    path("mot-de-passe-oublie/envoye/", auth_views.PasswordResetDoneView.as_view(
        template_name="registration/password_reset_done.html",
    ), name="password_reset_done"),
    path("reinitialiser-mot-de-passe/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name="registration/password_reset_confirm.html",
        success_url=reverse_lazy("password_reset_complete"),
    ), name="password_reset_confirm"),
    path("reinitialiser-mot-de-passe/termine/", auth_views.PasswordResetCompleteView.as_view(
        template_name="registration/password_reset_complete.html",
    ), name="password_reset_complete"),
    # Offres
    path("offres/", views.offres_index, name="offres_index"),
    path("offres/<int:pk>/", views.offres_show, name="offres_show"),
    # Espace étudiant
    path("etudiant/dashboard/", views.student_dashboard, name="student_dashboard"),
    path("etudiant/profil/modifier/", views.student_profile_edit, name="student_profile_edit"),
    # Espace entreprise
    path("entreprise/dashboard/", views.company_dashboard, name="company_dashboard"),
    path("entreprise/profil/modifier/", views.company_profile_edit, name="company_profile_edit"),
    path("entreprise/offres/create/", views.offres_create, name="offres_create"),
    path("entreprise/mes-offres/", views.offres_company, name="offres_company"),
    path("entreprise/offres/<int:pk>/edit/", views.offres_edit, name="offres_edit"),
    path("entreprise/offres/<int:pk>/delete/", views.offres_destroy, name="offres_destroy"),
    # Candidatures
    path("offres/<int:pk>/postuler/", views.applications_store, name="applications_store"),
    path("mes-candidatures/", views.applications_my, name="applications_my"),
    path("entreprise/candidatures/", views.applications_company, name="applications_company"),
    path("entreprise/candidatures/<int:pk>/cv/", views.applications_download_cv, name="applications_download_cv"),
    path("entreprise/candidatures/<int:pk>/lettre/", views.applications_download_cover_letter, name="applications_download_cover_letter"),
    path("candidatures/<int:pk>/accepter/", views.applications_accept, name="applications_accept"),
    path("candidatures/<int:pk>/refuser/", views.applications_reject, name="applications_reject"),
    # Administration
    path("admin-stagehub/dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("admin-stagehub/utilisateurs/", views.admin_users_index, name="admin_users_index"),
    path("admin-stagehub/utilisateurs/<int:pk>/delete/", views.admin_users_destroy, name="admin_users_destroy"),
    path("admin-stagehub/offres/", views.admin_offers_index, name="admin_offers_index"),
    path("admin-stagehub/offres/<int:pk>/delete/", views.admin_offers_destroy, name="admin_offers_destroy"),
    path("admin-stagehub/import-linkedin/", views.admin_import_linkedin, name="admin_import_linkedin"),
    # API JSON
    path("api/offres/", views.api_offers, name="api_offers"),
    path("api/offres/<int:pk>/", views.api_offer_detail, name="api_offer_detail"),
    path("api/offres/<int:pk>/match/<int:student_pk>/", views.api_match_score, name="api_match_score"),
]
