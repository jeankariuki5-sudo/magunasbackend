from django.db import models
from accounts.models import User, BaseModel
from products.models import BranchProduct
from branches.models import Branch, DeliveryZone

# Create your models here.
# ========================================
# Cart Model
# ========================================
class Cart(BaseModel):
    customer = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='cart')

    def __str__(self):
        return f"cart of {self.customer.username} @ {self.branch}"
   

# ========================================
# Cart Item Model
# ========================================
class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    branch_product = models.ForeignKey(BranchProduct, on_delete=models.CASCADE, related_name='cart_items')
    quantity = models.PositiveIntegerField(default=1)

    @property
    def subtotal(self):
        return self.branch_product.price * self.quantity
    
    def __str__(self):
        return f"{self.quantity} x {self.branch_product.product.product_name}"
    

# ========================================
# Order Model
# ========================================
class Order(BaseModel):
    STATUS_CHOICES = [
        ('placed', 'Placed'),
        ('packed', 'Packed'),
        ('out_for_delivery', 'Out for Delivery'),
        ('ready_for_pickup', 'Ready for Pickup'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    FULFILLMENT_CHOICES = [
        ('delivery', 'Delivery'),
        ('pickup', 'Pickup')
    ]

    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='orders')
    fulfillment_type = models.CharField(max_length=10, choices=FULFILLMENT_CHOICES)
    delivery_zone = models.ForeignKey(DeliveryZone, on_delete=models.SET_NULL, null=True, blank=True)
    delivery_address = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='placed')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    def __str__(self):
        return f"Order #{self.id} by {self.customer.username}"


# ===============================================
# Order item Model
# ===============================================
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    branch_product = models.ForeignKey(BranchProduct, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def subtotal(self):
        return self.unit_price * self.quantity
    
    def __str__(self):
        return f"{self.quantity} x {self.branch_product.product.product_name} (order #{self.order.id})"