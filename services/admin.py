from django.contrib import admin
from .models import Months, Months_calculation, Month_indicators


@admin.register(Months)
class MonthsAdmin(admin.ModelAdmin):
    list_display = ("month_id", "month_name", "status", "base_yield", "ideal_temp", "ideal_precip")
    list_filter = ("status",)
    search_fields = ("month_name",)


class OrderServiceInline(admin.TabularInline):
    model = Month_indicators
    extra = 0


@admin.register(Months_calculation)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "created_at", "created_by", "submitted_at", "finished_at")
    list_filter = ("status",)
    search_fields = ("id", "created_by__username")
    inlines = [OrderServiceInline]


@admin.register(Month_indicators)
class OrderServiceAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "service", "avg_temp", "sum_precipitation")
    list_filter = ("order", "service")
    search_fields = ("order__id", "service__month_name")
