from django.db import models
from django.contrib.auth.models import AbstractUser
import random
from django.utils import timezone
from datetime import timedelta


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class User(BaseModel, AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('customer', 'Customer'),
        ('branch_manager', 'Branch Manager'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')
    phone_number = models.CharField(max_length=15, blank=True, unique=True)

    def is_admin(self):
        return self.role == 'admin'

    def is_customer(self):
        return self.role == 'customer'

    def is_branch_manager(self):
        return self.role == 'branch_manager'

    def __str__(self):
        return f"{self.username} ({self.role})"


# =========================================
# Customer Profile
# =========================================
class CustomerProfile(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    profile_picture = models.ImageField(upload_to='customer_profiles/', blank=True, null=True)
    default_delivery_address = models.TextField(blank=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.user.username})"


# =========================================
# Branch Manager Profile
# =========================================
class BranchManagerProfile(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='manager_profile')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    national_id = models.CharField(max_length=20, unique=True)
    profile_picture = models.ImageField(upload_to='manager_profiles/', blank=True, null=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} - Manager ({self.user.username})"
    


# ===========================================================
# Account suspention model
# ===========================================================
class AccountSuspension(models.Model):
    SUSPENSION_TYPES = [
        ('permanent', 'Permanent'),
        ('temporary', 'Temporary'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='suspension')
    suspension_type = models.CharField(max_length=10, choices=SUSPENSION_TYPES)
    reason = models.TextField()
    suspended_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='suspensions_issued')
    suspended_at = models.DateTimeField(auto_now_add=True)

    # only for temporary
    lift_at = models.DateTimeField(null=True, blank=True)  

    def __str__(self):
        return f"{self.user.username} suspended ({self.suspension_type})"


# ===========================================================
#  OTP model
# ===========================================================
class PasswordResetOTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reset_otps')
    otp = models.CharField(max_length=6)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at

    @classmethod
    def generate_otp(cls, user):
        # Invalidate any existing unused OTPs for this user
        cls.objects.filter(user=user, is_used=False).delete()

        otp = str(random.randint(100000, 999999))
        expires_at = timezone.now() + timedelta(minutes=10)  # OTP valid for 10 minutes

        return cls.objects.create(
            user=user,
            otp=otp,
            expires_at=expires_at
        )

    def __str__(self):
        return f"OTP for {self.user.username} - {'used' if self.is_used else 'active'}"
    


# ===============================================================
# Feedback model
# ===============================================================
class Feedback(BaseModel):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('reviewed', 'Reviewed'),
        ('resolved', 'Resolved'),
    ]

    TYPE_CHOICES = [
        ('general', 'General'),
        ('order', 'Order'),
        ('branch', 'Branch'),
        ('product', 'Product'),
    ]

    submitted_by = models.ForeignKey(
        User,
        on_delete = models.CASCADE,
        related_name = 'feedback',

    )
    branch = models.ForeignKey(
        'branches.Branch',
        on_delete = models.SET_NULL,
        null = True,
        blank = True,
        related_name = 'feedback'
    )
    order = models.ForeignKey(
        'orders.Order',
        on_delete = models.SET_NULL,
        null = True,
        blank = True,
        related_name = 'feedback'
    )
    feedback_type = models.CharField(max_length = 10, choices = TYPE_CHOICES, default = 'general')
    title = models.CharField(max_length = 200)
    description = models.TextField()
    status = models.CharField(max_length = 10, choices = STATUS_CHOICES, default = 'pending')

    def __str__(self):
        return f"{self.submitted_by.username} - {self.title} ({self.status})"