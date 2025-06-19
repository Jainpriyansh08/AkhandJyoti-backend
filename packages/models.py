from django.db import models

# Create your models here.

class Package(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    base_amount = models.DecimalField(max_digits=10, decimal_places=2)
    discounted_amount = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
