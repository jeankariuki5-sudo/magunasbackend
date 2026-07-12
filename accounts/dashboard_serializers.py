from rest_framework import serializers
from orders.models import Order, OrderItem
from products.models import BranchProduct
from .models import AccountSuspension


class OrderItemSerializer(serializers.ModelSerializer):
    product = serializers.CharField(source = 'branch_product.product.product_name', read_only = True)

    class Meta:
        model = OrderItem
        fields = ['product', 'quantity', 'unit_price', 'subtotal']


class OrderSerializer(serializers.ModelSerializer):
    customer = serializers.CharField(source = 'customer.username', read_only = True)
    branch = serializers.CharField(source = 'branch.branch_name', read_only = True)
    items = OrderItemSerializer(many = True, read_only = True)

    class Meta:
        model = Order
        fields = [
            'id',
            'customer',
            'branch',
            'status',
            'fulfillment_type',
            'total_amount',
            'delivery_fee',
            'created_at',
            'items'
        ]


class LowStockSerializer(serializers.ModelSerializer):
    product = serializers.CharField(source = 'product.product_name', read_only = True)
    branch = serializers.CharField(source = 'branch.branch_name', read_only = True)

    class Meta:
        model = BranchProduct
        fields = ['product', 'branch', 'stock_quantity', 'price']


class SuspensionSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source = 'user.username', read_only = True)
    suspended_by = serializers.CharField(source = 'suspended_by.username', read_only  =True)

    class Meta:
        model = AccountSuspension
        fields = [
            'user',
            'suspension_type',
            'reason',
            'suspended_by',
            'suspended_at',
            'lift_at'
        ]