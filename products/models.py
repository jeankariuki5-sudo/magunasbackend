from django.db import models
from accounts.models import BaseModel
from branches.models import Branch

# Create your models here.
# =========================================
# Product category Model
# =========================================
class Category(models.Model):
    category_name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    image = models.ImageField(upload_to='category_images/', blank=True, null=True)

    def __str__(self):
        return self.category_name
    

# =========================================
# Product Model
# =========================================
class Product(BaseModel):
    product_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    image = models.ImageField(upload_to='product_images/', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.product_name
    

# ========================================
# BranchProduct Model
# ========================================
class BranchProduct(BaseModel):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='branch_products')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='branch_products')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.PositiveIntegerField(default=0)
    is_available = models.BooleanField(default=True)

    class Meta:
        unique_together = ('branch', 'product')

    @property
    def in_stock(self):
        return self.stock_quantity > 0

    def __str__(self):
        return f"{self.product.product_name} @ {self.branch.branch_name}"