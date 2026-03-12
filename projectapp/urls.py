from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("jobs/", views.jobs_list, name="jobs_list"),
    path("jobs/<int:pk>/", views.job_detail, name="job_detail"),
    path("jobs/<int:pk>/apply/", views.job_apply, name="job_apply"),
    path("jobs/<int:pk>/applications/", views.job_applications, name="job_applications"),
    path("applications/<int:pk>/review/", views.application_review, name="application_review"),
    path("jobs/create/", views.job_create, name="job_create"),
    path("jobs/<int:pk>/edit/", views.job_edit, name="job_edit"),
    path("jobs/<int:pk>/delete/", views.job_delete, name="job_delete"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("hr/<int:pk>/approve/", views.hr_approve, name="hr_approve"),
    path("applications/<int:pk>/toggle-showcase/", views.application_toggle_showcase, name="application_toggle_showcase"),
    path("portfolio/add/", views.portfolio_add, name="portfolio_add"),
    path("profile/", views.profile_view, name="profile"),
    path("portfolio/", views.portfolio_page, name="portfolio_page"),
    path("profile/edit/", views.profile_edit, name="profile_edit"),
    path("register/", views.register_choice, name="register"),
    path("register/student/", views.register_student, name="register_student"),
    path("register/hr/", views.register_hr, name="register_hr"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
]

