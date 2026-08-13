from django.db import models
from accounts.models import User
from accounts.models import BaseModel

# Create your models here.
class Branch(BaseModel):
    branch_name = models.CharField(max_length=100)
    address = models.CharField(max_length=200)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    phone_number = models.CharField(max_length=15)
    branch_manager = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_branch'
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.branch_name