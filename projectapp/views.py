from __future__ import annotations

from typing import Any, Dict, List

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Avg
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .models import Company, HRProfile, Job, JobApplication, PortfolioItem, StudentProfile


def home(request: HttpRequest) -> HttpResponse:
    return render(request, "core/home.html")


def about(request: HttpRequest) -> HttpResponse:
    return render(request, "core/about.html")


def jobs_list(request: HttpRequest) -> HttpResponse:
    jobs_qs = (
        Job.objects.filter(is_active=True, is_approved=True)
        .select_related("company")
        .order_by("-created_at")
    )
    category = request.GET.get("category", "").strip()
    if category:
        jobs_qs = jobs_qs.filter(category=category)
    jobs = list(jobs_qs)
    return render(
        request,
        "core/jobs_list.html",
        {"jobs": jobs, "selected_category": category},
    )


def job_detail(request: HttpRequest, pk: int) -> HttpResponse:
    job = get_object_or_404(
        Job.objects.select_related("company"),
        pk=pk,
        is_active=True,
        is_approved=True,
    )

    can_apply = (
        request.user.is_authenticated
        and StudentProfile.objects.filter(user=request.user).exists()
    )
    has_applied = False
    if can_apply:
        has_applied = JobApplication.objects.filter(job=job, student=request.user).exists()

    context = {
        "job": job,
        "can_apply": can_apply,
        "has_applied": has_applied,
    }
    return render(request, "core/job_detail.html", context)


@login_required
def job_apply(request: HttpRequest, pk: int) -> HttpResponse:
    job = get_object_or_404(
        Job.objects.select_related("company"),
        pk=pk,
        is_active=True,
        is_approved=True,
    )

    if not StudentProfile.objects.filter(user=request.user).exists():
        messages.error(request, "Faqat talaba profili orqali ariza yuborish mumkin.")
        return redirect("job_detail", pk=job.pk)

    if request.method == "POST":
        message_text = request.POST.get("message", "").strip()
        cv_url = request.POST.get("cv_url", "").strip()
        portfolio_url = request.POST.get("portfolio_url", "").strip()
        attachment = request.FILES.get("attachment")

        if JobApplication.objects.filter(job=job, student=request.user).exists():
            messages.info(request, "Siz bu eʼlonga allaqachon ariza yuborgansiz.")
            return redirect("job_detail", pk=job.pk)

        JobApplication.objects.create(
            job=job,
            student=request.user,
            message=message_text,
            cv_url=cv_url,
            portfolio_url=portfolio_url,
            attachment=attachment,
        )
        messages.success(request, "Arizangiz yuborildi.")
        return redirect("dashboard")

    return render(request, "core/job_apply.html", {"job": job})


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    user = request.user
    has_student = StudentProfile.objects.filter(user=user).exists()
    has_hr = HRProfile.objects.filter(user=user).exists()

    if has_student:
        applications = (
            JobApplication.objects.filter(student=user)
            .select_related("job", "job__company")
            .order_by("-created_at")
        )
        portfolio_items = (
            PortfolioItem.objects.filter(student=user)
            .select_related("job", "job__company")
            .order_by("-created_at")
        )
        student_apps = JobApplication.objects.filter(student=user)
        accepted_count = student_apps.filter(status="accepted").count()
        in_progress_count = student_apps.filter(status__in=("new", "viewed")).count()
        avg_rating = student_apps.aggregate(Avg("rating"))["rating__avg"]
        context = {
            "applications": applications,
            "portfolio_items": portfolio_items,
            "accepted_count": accepted_count,
            "in_progress_count": in_progress_count,
            "avg_rating": round(avg_rating, 1) if avg_rating is not None else None,
        }
        if user.is_staff:
            context["pending_hrs"] = (
                HRProfile.objects.filter(is_approved=False)
                .select_related("user", "company")
                .order_by("-created_at")
            )
        return render(request, "core/dashboard_student.html", context)

    if has_hr:
        jobs = Job.objects.filter(company=user.hr_profile.company).prefetch_related("applications")
        context = {"jobs": jobs}
        if user.is_staff:
            context["pending_hrs"] = (
                HRProfile.objects.filter(is_approved=False)
                .select_related("user", "company")
                .order_by("-created_at")
            )
        return render(request, "core/dashboard_hr.html", context)

    student_apps = JobApplication.objects.filter(student=user)
    accepted_count = student_apps.filter(status="accepted").count()
    in_progress_count = student_apps.filter(status__in=("new", "viewed")).count()
    avg_rating = student_apps.aggregate(Avg("rating"))["rating__avg"]
    context = {
        "accepted_count": accepted_count,
        "in_progress_count": in_progress_count,
        "avg_rating": round(avg_rating, 1) if avg_rating is not None else None,
    }
    if user.is_staff:
        context["pending_hrs"] = (
            HRProfile.objects.filter(is_approved=False)
            .select_related("user", "company")
            .order_by("-created_at")
        )
    return render(request, "core/dashboard.html", context)


@login_required
def profile_view(request: HttpRequest) -> HttpResponse:
    user = request.user
    user_role = None
    portfolio_items = None
    showcased_applications = None

    if StudentProfile.objects.filter(user=user).exists():
        user_role = "student"
        portfolio_items = (
            PortfolioItem.objects.filter(student=user)
            .select_related("job", "job__company")
            .order_by("-created_at")
        )
        showcased_applications = (
            JobApplication.objects.filter(student=user, show_on_profile=True)
            .select_related("job", "job__company")
            .order_by("-created_at")
        )
    elif HRProfile.objects.filter(user=user).exists():
        user_role = "hr"

    context: Dict[str, Any] = {
        "user_role": user_role,
        "portfolio_items": portfolio_items,
        "showcased_applications": showcased_applications,
    }
    return render(request, "core/profile.html", context)


@login_required
def portfolio_page(request: HttpRequest) -> HttpResponse:
    user = request.user
    if not StudentProfile.objects.filter(user=user).exists():
        messages.info(request, "Portfolio faqat talabalar uchun.")
        return redirect("dashboard")
    showcased_applications = (
        JobApplication.objects.filter(student=user, show_on_profile=True)
        .select_related("job", "job__company")
        .order_by("-created_at")
    )
    return render(
        request,
        "core/portfolio_page.html",
        {"showcased_applications": showcased_applications},
    )


@login_required
def profile_edit(request: HttpRequest) -> HttpResponse:
    user = request.user
    student_profile = StudentProfile.objects.filter(user=user).first()
    hr_profile = HRProfile.objects.filter(user=user).first()

    if student_profile:
        if request.method == "POST":
            user.email = request.POST.get("email", "").strip() or user.email
            user.save(update_fields=["email"])
            student_profile.full_name = request.POST.get("full_name", "").strip() or student_profile.full_name
            student_profile.university_name = request.POST.get("university_name", "").strip() or student_profile.university_name
            student_profile.faculty = request.POST.get("faculty", "").strip()
            student_profile.major = request.POST.get("major", "").strip()
            ey = request.POST.get("enrollment_year", "").strip()
            student_profile.enrollment_year = int(ey) if ey and ey.isdigit() else student_profile.enrollment_year
            ag = request.POST.get("age", "").strip()
            student_profile.age = int(ag) if ag and ag.isdigit() else student_profile.age
            student_profile.gender = request.POST.get("gender", "").strip()
            student_profile.phone = request.POST.get("phone", "").strip() or student_profile.phone
            student_profile.address = request.POST.get("address", "").strip()
            student_profile.skills = request.POST.get("skills", "").strip()
            student_profile.save()
            messages.success(request, "Profil yangilandi.")
            return redirect("profile")
        return render(request, "core/profile_edit_student.html", {"profile": student_profile})

    if hr_profile:
        if request.method == "POST":
            user.email = request.POST.get("email", "").strip() or user.email
            user.save(update_fields=["email"])
            hr_profile.full_name = request.POST.get("hr_full_name", "").strip() or hr_profile.full_name
            hr_profile.phone = request.POST.get("hr_phone", "").strip() or hr_profile.phone
            company = hr_profile.company
            company.name = request.POST.get("company_name", "").strip() or company.name
            company.address = request.POST.get("company_address", "").strip()
            company.email = request.POST.get("company_email", "").strip() or company.email
            company.industry = request.POST.get("company_industry", "").strip()
            company.save()
            hr_profile.save()
            messages.success(request, "Profil yangilandi.")
            return redirect("profile")
        return render(request, "core/profile_edit_hr.html", {"profile": hr_profile})

    messages.error(request, "Tahrirlash uchun talaba yoki HR profili kerak.")
    return redirect("profile")


def register_choice(request: HttpRequest) -> HttpResponse:
    return render(request, "core/register_choice.html")


@transaction.atomic
def register_student(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "").strip()

        full_name = request.POST.get("full_name", "").strip()
        university_name = request.POST.get("university_name", "").strip()
        faculty = request.POST.get("faculty", "").strip()
        major = request.POST.get("major", "").strip()
        enrollment_year = request.POST.get("enrollment_year") or None
        age = request.POST.get("age") or None
        gender = request.POST.get("gender", "").strip()
        phone = request.POST.get("phone", "").strip()
        address = request.POST.get("address", "").strip()
        skills = request.POST.get("skills", "").strip()

        errors: List[str] = []
        if not username or not email or not password or not full_name or not university_name or not phone:
            errors.append("Majburiy maydonlarni toʻldiring.")
        if User.objects.filter(username=username).exists():
            errors.append("Bu foydalanuvchi nomi band.")
        if User.objects.filter(email=email).exists():
            errors.append("Bu email bilan allaqachon roʻyxatdan oʻtilgan.")

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, "core/register_student.html")

        user = User.objects.create_user(username=username, email=email, password=password)

        StudentProfile.objects.create(
            user=user,
            university_name=university_name,
            faculty=faculty,
            major=major,
            enrollment_year=int(enrollment_year) if enrollment_year else None,
            full_name=full_name,
            age=int(age) if age else None,
            gender=gender,
            phone=phone,
            address=address,
            skills=skills,
        )

        login(request, user)
        return redirect("dashboard")

    return render(request, "core/register_student.html")


@transaction.atomic
def register_hr(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "").strip()

        company_name = request.POST.get("company_name", "").strip()
        company_address = request.POST.get("company_address", "").strip()
        company_email = request.POST.get("company_email", "").strip()
        company_industry = request.POST.get("company_industry", "").strip()

        hr_full_name = request.POST.get("hr_full_name", "").strip()
        hr_phone = request.POST.get("hr_phone", "").strip()

        errors: List[str] = []
        if not username or not email or not password:
            errors.append("Tizimga kirish uchun maydonlar majburiy.")
        if not company_name or not company_email:
            errors.append("Kompaniya nomi va email majburiy.")
        if not hr_full_name or not hr_phone:
            errors.append("HR maʼlumotlari majburiy.")
        if User.objects.filter(username=username).exists():
            errors.append("Bu foydalanuvchi nomi band.")
        if User.objects.filter(email=email).exists():
            errors.append("Bu email bilan allaqachon roʻyxatdan oʻtilgan.")

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, "core/register_hr.html")

        user = User.objects.create_user(username=username, email=email, password=password)
        company = Company.objects.create(
            name=company_name,
            address=company_address,
            email=company_email,
            industry=company_industry,
        )
        HRProfile.objects.create(
            user=user,
            company=company,
            full_name=hr_full_name,
            phone=hr_phone,
        )

        login(request, user)
        return redirect("dashboard")

    return render(request, "core/register_hr.html")


def login_view(request: HttpRequest) -> HttpResponse:
    next_url = request.POST.get("next") or request.GET.get("next") or "/dashboard/"

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect(next_url)
        form = {"errors": True}
        return render(request, "core/login.html", {"form": form, "next": next_url})

    return render(request, "core/login.html", {"next": next_url})


@login_required
def logout_view(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        logout(request)
        return redirect("home")
    return redirect("home")


@login_required
def hr_approve(request: HttpRequest, pk: int) -> HttpResponse:
    if not request.user.is_staff:
        messages.error(request, "Faqat admin HR larni tasdiqlashi mumkin.")
        return redirect("dashboard")
    hr_profile = get_object_or_404(HRProfile, pk=pk)
    action = request.POST.get("action", "approve")
    if action == "approve":
        hr_profile.is_approved = True
        hr_profile.save()
        messages.success(
            request,
            f"{hr_profile.full_name} ({hr_profile.company.name}) tasdiqlandi. Endi ish eʼlonlarini joylashi mumkin.",
        )
    elif action == "reject":
        hr_profile.is_approved = False
        hr_profile.save()
        messages.info(request, f"{hr_profile.full_name} tasdiqdan chiqarildi.")
    return redirect("dashboard")


@login_required
def portfolio_add(request: HttpRequest) -> HttpResponse:
    if not StudentProfile.objects.filter(user=request.user).exists():
        messages.error(request, "Faqat talaba profili portfolio qoʻshishi mumkin.")
        return redirect("dashboard")

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        description = request.POST.get("description", "").strip()
        attachment = request.FILES.get("attachment")
        link = request.POST.get("link", "").strip()

        if not title:
            messages.error(request, "Ish nomi majburiy.")
            return render(request, "core/portfolio_form.html")

        PortfolioItem.objects.create(
            student=request.user,
            title=title,
            description=description,
            attachment=attachment,
            link=link,
        )
        messages.success(request, "Portfolio ga ish qoʻshildi.")
        return redirect("dashboard")

    return render(request, "core/portfolio_form.html")


@login_required
def job_create(request: HttpRequest) -> HttpResponse:
    hr_profile = HRProfile.objects.filter(user=request.user).first()
    if not hr_profile:
        messages.error(request, "Faqat HR profili eʼlon joylashi mumkin.")
        return redirect("dashboard")
    if not hr_profile.is_approved:
        messages.error(
            request,
            "Ish eʼlonlarini joylash uchun admin sizning hisobingizni tasdiqlashi kerak. "
            "Iltimos, kuting yoki admin bilan bogʻlaning.",
        )
        return redirect("dashboard")

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        category = request.POST.get("category", "").strip()
        description = request.POST.get("description", "").strip()
        requirements = request.POST.get("requirements", "").strip()
        attachment = request.FILES.get("attachment")
        link = request.POST.get("link", "").strip()

        if not title or not requirements:
            messages.error(request, "Elon nomi va shartlar majburiy.")
            return render(request, "core/job_form.html", {"form_type": "create"})

        Job.objects.create(
            company=hr_profile.company,
            title=title,
            category=category,
            description=description,
            requirements=requirements,
            attachment=attachment,
            link=link,
            is_approved=True,
        )
        messages.success(request, "Eʼlon qoʻshildi va hammaga koʻrinadi.")
        return redirect("dashboard")

    return render(request, "core/job_form.html", {"form_type": "create"})


@login_required
def job_edit(request: HttpRequest, pk: int) -> HttpResponse:
    if not HRProfile.objects.filter(user=request.user).exists():
        messages.error(request, "Faqat HR profili eʼlon tahrirlashi mumkin.")
        return redirect("dashboard")

    job = get_object_or_404(Job, pk=pk, company=request.user.hr_profile.company)

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        category = request.POST.get("category", "").strip()
        description = request.POST.get("description", "").strip()
        requirements = request.POST.get("requirements", "").strip()
        attachment = request.FILES.get("attachment")
        link = request.POST.get("link", "").strip()
        is_active = bool(request.POST.get("is_active"))

        if not title or not requirements:
            messages.error(request, "Elon nomi va shartlar majburiy.")
            return render(request, "core/job_form.html", {"form_type": "edit", "job": job})

        job.title = title
        job.category = category
        job.description = description
        job.requirements = requirements
        if attachment:
            job.attachment = attachment
        job.link = link
        job.is_active = is_active
        job.save()

        messages.success(request, "Eʼlon yangilandi.")
        return redirect("dashboard")

    return render(request, "core/job_form.html", {"form_type": "edit", "job": job})


@login_required
def job_applications(request: HttpRequest, pk: int) -> HttpResponse:
    if not HRProfile.objects.filter(user=request.user).exists():
        messages.error(request, "Faqat HR profili arizalarni koʻrishi mumkin.")
        return redirect("dashboard")

    job = get_object_or_404(Job, pk=pk, company=request.user.hr_profile.company)
    applications = list(
        JobApplication.objects.filter(job=job)
        .select_related("student")
        .order_by("-created_at")
    )

    # Yangi arizalarni ko‘rilgan deb belgilash
    JobApplication.objects.filter(job=job, status="new").update(status="viewed")

    students: List[Dict[str, Any]] = []
    for app in applications:
        profile = getattr(app.student, "student_profile", None)
        students.append({"application": app, "profile": profile})

    context = {
        "job": job,
        "students": students,
    }
    return render(request, "core/job_applications.html", context)


@login_required
def application_review(request: HttpRequest, pk: int) -> HttpResponse:
    if request.method != "POST":
        return redirect("dashboard")

    if not HRProfile.objects.filter(user=request.user).exists():
        messages.error(request, "Faqat HR profili baholashi mumkin.")
        return redirect("dashboard")

    app = get_object_or_404(
        JobApplication.objects.select_related("job", "job__company"),
        pk=pk,
        job__company=request.user.hr_profile.company,
    )

    rating_raw = (request.POST.get("rating") or "").strip()
    comment = (request.POST.get("hr_comment") or "").strip()

    rating = None
    if rating_raw:
        try:
            rating = int(rating_raw)
        except ValueError:
            rating = None

    if rating is not None and not (1 <= rating <= 5):
        messages.error(request, "Baho 1 dan 5 gacha bo‘lishi kerak.")
        return redirect("job_applications", pk=app.job.pk)

    app.rating = rating
    app.hr_comment = comment
    app.save(update_fields=["rating", "hr_comment", "updated_at"])

    messages.success(request, "Baholandi va izoh saqlandi.")
    return redirect("job_applications", pk=app.job.pk)


@login_required
def application_toggle_showcase(request: HttpRequest, pk: int) -> HttpResponse:
    if request.method != "POST":
        return redirect("dashboard")

    if not StudentProfile.objects.filter(user=request.user).exists():
        messages.error(request, "Faqat talaba profili o'z arizasini profilga qo'sha oladi.")
        return redirect("dashboard")

    app = get_object_or_404(
        JobApplication.objects.select_related("job"),
        pk=pk,
        student=request.user,
    )

    app.show_on_profile = not app.show_on_profile
    app.save(update_fields=["show_on_profile", "updated_at"])

    if app.show_on_profile:
        messages.success(request, "Ariza profilingizda ko‘rsatiladigan bo‘ldi.")
    else:
        messages.success(request, "Ariza profilingizdan olib tashlandi.")

    return redirect("dashboard")


@login_required
def job_delete(request: HttpRequest, pk: int) -> HttpResponse:
    if request.method != "POST":
        return redirect("dashboard")

    if not HRProfile.objects.filter(user=request.user).exists():
        messages.error(request, "Faqat HR profili eʼlonni o'chira oladi.")
        return redirect("dashboard")

    job = get_object_or_404(Job, pk=pk, company=request.user.hr_profile.company)
    job.delete()
    messages.success(request, "Eʼlon o‘chirildi.")
    return redirect("dashboard")

