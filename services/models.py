from django.db import models
    class Service(models.Model):
        name = models.CharField(max_length=255)
        description = models.TextField()
        image = models.ImageField(upload_to='services/')
        created_at = models.DateTimeField(auto_now_add=True)
        updated_at = models.DateTimeField(auto_now=True)

        def __str__(self):
            return self.name
# Create your models here.
