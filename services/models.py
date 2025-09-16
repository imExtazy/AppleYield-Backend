from django.db import models

class Service(models.Model):
    STATUSES = [
        ("active", "Активна"),
        ("deleted", "Удалена"),
    ]

    name = models.CharField(max_length=200)  
    description = models.TextField()  
    main_value = models.TextField() 
    image_key = models.CharField(max_length=255, null=True, blank=True)  
    temperature = models.CharField(max_length=100, null=True, blank=True)  
    precipitation = models.CharField(max_length=100, null=True, blank=True)  
    status = models.CharField(
        max_length=20,
        choices=STATUSES,
        default="active",
    )

    def __str__(self):
        return self.name


class Order(models.Model):
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
    moderator = models.ForeignKey(
        User, related_name="moderated_orders",
        on_delete=models.PROTECT, null=True, blank=True
    )

    location = models.CharField(max_length=50, choices=LOCATIONS)
    person = models.CharField(max_length=50, choices=PERSONS)

    def __str__(self):
        return f"Order {self.id} ({self.status})"


    class Meta:
        unique_together = ("order", "service")

class OrderService(models.Model):
    order = models.ForeignKey(Order, on_delete=models.PROTECT)
    service = models.ForeignKey(Service, on_delete=models.PROTECT)
    sum_precipitation = models.FloatField()
    avg_temp = models.FloatField()
    comment = models.TextField(null=True, blank=True)        
# Create your models here.