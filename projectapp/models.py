from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Company(TimeStampedModel):
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255, blank=True)
    email = models.EmailField()
    industry = models.CharField(max_length=255, blank=True)

    def __str__(self) -> str:
        return self.name


class StudentProfile(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="student_profile")
    university_name = models.CharField(max_length=255)
    faculty = models.CharField(max_length=255, blank=True)
    major = models.CharField(max_length=255, blank=True)
    enrollment_year = models.PositiveIntegerField(null=True, blank=True)
    full_name = models.CharField(max_length=255)
    age = models.PositiveIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=1, blank=True)
    phone = models.CharField(max_length=32)
    address = models.CharField(max_length=255, blank=True)
    skills = models.TextField(blank=True)

    def __str__(self) -> str:
        return self.full_name or self.user.username


class HRProfile(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="hr_profile")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="hr_profiles")
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=32)
    is_approved = models.BooleanField(
        default=False,
        verbose_name="Tasdiqlangan",
        help_text="Admin tasdiqlagach, HR ish eʼlonlarini joylashi mumkin.",
    )

    class Meta:
        verbose_name = "HR hodim"
        verbose_name_plural = "HR hodimlar (tasdiqlash)"

    def __str__(self) -> str:
        return f"{self.full_name} — {self.company.name}"


class Job(TimeStampedModel):
    CATEGORY_CHOICES = [
        ("it", "IT / Dasturlash"),
        ("education", "Taʼlim / Oʻqituvchi"),
        ("design", "Dizayn"),
        ("marketing", "Marketing"),
        ("finance", "Moliya / Buxgalteriya"),
        ("sales", "Savdo"),
        ("other", "Boshqa"),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="jobs")
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES, blank=True)
    description = models.TextField(blank=True)
    requirements = models.TextField()
    attachment = models.FileField(upload_to="job_attachments/", blank=True, null=True)
    link = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    is_approved = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.title


class JobApplication(TimeStampedModel):
    STATUS_CHOICES = [
        ("new", "Yangi"),
        ("viewed", "Koʻrib chiqilgan"),
        ("accepted", "Qabul qilingan"),
        ("rejected", "Rad etilgan"),
    ]

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="applications")
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="job_applications")
    message = models.TextField(blank=True)
    cv_url = models.URLField(blank=True)
    portfolio_url = models.URLField(blank=True)
    attachment = models.FileField(upload_to="application_attachments/", blank=True, null=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="new")
    rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    hr_comment = models.TextField(blank=True)
    show_on_profile = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"{self.student.username} → {self.job.title}"


class PortfolioItem(TimeStampedModel):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="portfolio_items")
    job = models.ForeignKey(Job, on_delete=models.SET_NULL, null=True, blank=True, related_name="portfolio_items")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    attachment = models.FileField(upload_to="portfolio_attachments/", blank=True, null=True)
    link = models.URLField(blank=True)

    def __str__(self) -> str:
        return self.title

