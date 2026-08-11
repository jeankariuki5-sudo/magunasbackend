from django.db import models
from django.conf import settings
from django.utils import timezone

# Create your models here.
# ========================================
# Loyalty Account
# ========================================
class LoyaltyAccount(models.Model):
    customer = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete = models.CASCADE, related_name = 'loyalty_account'
    )
    points_balance = models.PositiveIntegerField(default = 0)
    lifetime_points_earned = models.PositiveIntegerField(default = 0)
    updated_at = models.DateTimeField(auto_now = True)

    def __str__(self):
        return f"{self.customer.username} - {self.points_balance} pts"


# ========================================
# Loyalty Transaction
# ========================================
class LoyaltyTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('earned', 'Earned'),
        ('redeemed', 'Redeemed'),
        ('reversed', 'Reversed'),  # points refunded, e.g. a redemption on an order that got cancelled
    ]

    account = models.ForeignKey(LoyaltyAccount, on_delete = models.CASCADE, related_name = 'transactions')
    order = models.ForeignKey(
        'orders.Order', on_delete = models.SET_NULL, null = True, blank = True, related_name = 'loyalty_transactions'
    )
    transaction_type = models.CharField(max_length = 10, choices = TRANSACTION_TYPES)
    points = models.IntegerField()  # positive for earned/reversed, negative for redeemed
    created_at = models.DateTimeField(auto_now_add = True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.account.customer.username} - {self.transaction_type} - {self.points} pts"


# ========================================
# Promotion
# ========================================
class Promotion(models.Model):
    branch_product = models.ForeignKey(
        'products.BranchProduct', on_delete = models.CASCADE, related_name = 'promotions'
    )
    discounted_price = models.DecimalField(max_digits = 10, decimal_places = 2)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    is_active = models.BooleanField(default = True)  # manual kill-switch, independent of the time window
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete = models.SET_NULL, null = True, related_name = 'created_promotions'
    )
    created_at = models.DateTimeField(auto_now_add = True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.branch_product} -> KES {self.discounted_price}"

    def is_currently_active(self):
        now = timezone.now()
        return self.is_active and self.start_datetime <= now <= self.end_datetime
