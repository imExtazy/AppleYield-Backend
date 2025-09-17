from django.contrib import admin
from .models import Service, Order, OrderService


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "status", "base_yield", "ideal_temp", "ideal_precip")
    list_filter = ("status",)
    search_fields = ("name",)


class OrderServiceInline(admin.TabularInline):
    model = OrderService
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "created_at", "created_by", "submitted_at", "finished_at")
    list_filter = ("status",)
    search_fields = ("id", "created_by__username")
    inlines = [OrderServiceInline]


@admin.register(OrderService)
class OrderServiceAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "service", "avg_temp", "sum_precipitation")
    list_filter = ("order", "service")
    search_fields = ("order__id", "service__name")
