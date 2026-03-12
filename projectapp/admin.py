from django.contrib import admin

from .models import Company, HRProfile, Job, JobApplication, PortfolioItem, StudentProfile


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "industry", "created_at")
    search_fields = ("name", "email", "industry")


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("full_name", "university_name", "major", "phone")
    search_fields = ("full_name", "university_name", "major", "phone")


@admin.register(HRProfile)
class HRProfileAdmin(admin.ModelAdmin):
    list_display = ("full_name", "company", "phone", "user", "is_approved", "created_at")
    list_display_links = ("full_name", "company")
    list_filter = ("is_approved", "created_at")
    search_fields = ("full_name", "company__name", "phone", "user__username", "user__email")
    list_editable = ("is_approved",)
    list_per_page = 25
    ordering = ("-created_at",)
    actions = ("approve_hr", "reject_hr")

    @admin.action(description="Tanlangan HR larni tasdiqlash")
    def approve_hr(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f"{updated} ta HR tasdiqlandi. Endi ular ish eʼlonlarini joylashi mumkin.")

    @admin.action(description="Tanlangan HR lardan tasdiqni olib tashlash")
    def reject_hr(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f"{updated} ta HR tasdiqdan chiqarildi.")


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ("title", "company", "category", "is_active", "is_approved", "created_at")
    list_filter = ("is_active", "is_approved", "category", "company")
    search_fields = ("title", "company__name")
    list_editable = ("is_active", "is_approved")


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ("job", "student", "status", "rating", "show_on_profile", "created_at")
    list_filter = ("status", "job__company", "rating", "show_on_profile")
    search_fields = ("job__title", "student__username", "student__email")


@admin.register(PortfolioItem)
class PortfolioItemAdmin(admin.ModelAdmin):
    list_display = ("title", "student", "job", "created_at")
    search_fields = ("title", "student__username")
