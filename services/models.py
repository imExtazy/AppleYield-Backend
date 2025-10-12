from django.db import models
from django.contrib.auth.models import User

class Months(models.Model):
    month_id = models.AutoField(primary_key=True)
    month_name = models.CharField(max_length=200)
    description = models.TextField()
    main_value = models.TextField()
    month_image = models.CharField(max_length=255, null=True, blank=True)
    status = models.BooleanField(default=True)

    # Параметры расчёта и фактические показатели месяца
    base_yield = models.DecimalField(max_digits=10, decimal_places=2)
    ideal_temp = models.DecimalField(max_digits=5, decimal_places=2)
    ideal_precip = models.IntegerField()
    temperature = models.DecimalField(max_digits=5, decimal_places=2)
    precipitation = models.IntegerField()

    class Meta:
        db_table = "services_months"

    def __str__(self):
        return self.month_name


class Months_calculation(models.Model):
    STATUSES = [
        ("draft", "Черновик"),
        ("deleted", "Удалён"),
        ("submitted", "Сформирован"),
        ("finished", "Завершён"),
        ("rejected", "Отклонён"),
    ]

    LOCATIONS = [
        ("moscow", "Москва"),
        ("spb", "Санкт-Петербург"),
        ("kazan", "Казань"),
    ]

    PERSONS = [
        ("ivanov", "Иванов И.И."),
        ("petrov", "Петров П.П."),
        ("sidorov", "Сидоров С.С."),
    ]

    status = models.CharField(max_length=20, choices=STATUSES, default="draft")
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    submitted_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    moderator = models.ForeignKey(User, related_name="moderated_orders", on_delete=models.PROTECT, null=True, blank=True)

    # Предметные поля заявки
    location = models.CharField(max_length=50, choices=LOCATIONS, default="moscow")
    person = models.CharField(max_length=50, choices=PERSONS, default="ivanov")
    # Результат расчёта (сохраняется при завершении заявки)
    result_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = "services_months_calculation"

    def __str__(self):
        return f"Order {self.id} ({self.status})"


class Month_indicators(models.Model):
    order = models.ForeignKey(Months_calculation, on_delete=models.PROTECT)
    service = models.ForeignKey(Months, on_delete=models.PROTECT)
    sum_precipitation = models.DecimalField(max_digits=10, decimal_places=2)
    avg_temp = models.DecimalField(max_digits=5, decimal_places=2)
    comment = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "services_month_indicators"
        unique_together = ("order", "service")

    def __str__(self):
        return f"OrderService(order={self.order_id}, service={self.service_id})"

# Create your models here.