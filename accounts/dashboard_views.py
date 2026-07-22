from datetime import timedelta
from django.db.models import Sum
from django.utils import timezone
from rest_framework import generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .permissions import IsAdmin, IsBranchManager, IsCustomer
from .models import User, AccountSuspension
from .dashboard_serializers import (
    OrderSerializer,
    LowStockSerializer,
    SuspensionSerializer
)
from branches.models import Branch
from products.models import BranchProduct
from orders.models import Order


# ══════════════════════════════════════════════════════
# ADMIN DASHBOARD
# ══════════════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([IsAdmin])
def AdminDashboard(request):
    # ── Users ──
    total_customers = User.objects.filter(role = 'customer').count()
    total_managers = User.objects.filter(role = 'branch_manager').count()
    total_suspended = AccountSuspension.objects.count()

    # ── Branches ──
    total_branches = Branch.objects.count()
    active_branches = Branch.objects.filter(is_active = True).count()
    inactive_branches = Branch.objects.filter(is_active = False).count()

    # ── Orders ──
    all_orders = Order.objects.all()
    total_orders = all_orders.count()
    pending_orders = all_orders.filter(status = 'placed').count()
    completed_orders = all_orders.filter(status = 'completed').count()
    cancelled_orders = all_orders.filter(status = 'cancelled').count()

    # ── Revenue ──
    total_revenue = all_orders.filter(
        status = 'completed'
    ).aggregate(total = Sum('total_amount'))['total'] or 0

    # ── Recent orders ──
    recent_orders = Order.objects.select_related(
        'customer', 'branch'
    ).order_by('-created_at')[:10]
    recent_orders_data = OrderSerializer(recent_orders, many = True).data

    # ── Low stock products (stock < 10) ──
    low_stock = BranchProduct.objects.filter(
        stock_quantity__lt = 10,
        is_available = True
    ).select_related('product', 'branch')
    low_stock_data = LowStockSerializer(low_stock, many = True).data

    # ── Recent suspensions ──
    suspensions = AccountSuspension.objects.select_related(
        'user', 'suspended_by'
    ).order_by('-suspended_at')[:5]
    suspensions_data = SuspensionSerializer(suspensions, many = True).data

    return Response({
        'users': {
            'total_customers': total_customers,
            'total_branch_managers': total_managers,
            'total_suspended': total_suspended,
        },
        'branches': {
            'total': total_branches,
            'active': active_branches,
            'inactive': inactive_branches,
        },
        'orders': {
            'total': total_orders,
            'pending': pending_orders,
            'completed': completed_orders,
            'cancelled': cancelled_orders,
        },
        'revenue': {
            'total': str(total_revenue),
        },
        'recent_orders': recent_orders_data,
        'low_stock_products': low_stock_data,
        'recent_suspensions': suspensions_data,
    }, status = 200)


# ══════════════════════════════════════════════════════
# BRANCH MANAGER DASHBOARD
# ══════════════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([IsBranchManager])
def BranchManagerDashboard(request):
    try:
        branch = request.user.managed_branch
    except Exception:
        return Response({'error': 'You are not assigned to any branch'}, status = 404)

    # ── Time settings ──
    today = timezone.now().date()
    month_start = today.replace(day = 1)

    # ── Branch orders ──
    branch_orders = Order.objects.filter(branch = branch)
    total_orders = branch_orders.count()
    pending_orders = branch_orders.filter(status = 'placed').count()
    packed_orders = branch_orders.filter(status = 'packed').count()
    out_for_delivery = branch_orders.filter(status = 'out_for_delivery').count()
    ready_for_pickup = branch_orders.filter(status = 'ready_for_pickup').count()
    completed_orders = branch_orders.filter(status = 'completed').count()
    cancelled_orders = branch_orders.filter(status = 'cancelled').count()

    # ── Revenue ──
    total_revenue = branch_orders.filter(
        status = 'completed'
    ).aggregate(total = Sum('total_amount'))['total'] or 0

    todays_revenue = branch_orders.filter(
        status = 'completed',
        created_at__date = today
    ).aggregate(total = Sum('total_amount'))['total'] or 0

    monthly_revenue = branch_orders.filter(
        status = 'completed',
        created_at__date__gte = month_start
    ).aggregate(total = Sum('total_amount'))['total'] or 0

    # ── Recent orders ──
    recent_orders = branch_orders.select_related(
        'customer', 'branch'
    ).order_by('-created_at')[:10]
    recent_orders_data = OrderSerializer(recent_orders, many = True).data

    # ── Low stock products ──
    low_stock = BranchProduct.objects.filter(
        branch = branch,
        stock_quantity__lt = 10,
        is_available = True
    ).select_related('product', 'branch')
    low_stock_data = LowStockSerializer(low_stock, many = True).data

    # ── Products summary ──
    total_products = BranchProduct.objects.filter(branch = branch).count()
    available_products = BranchProduct.objects.filter(
        branch = branch,
        is_available = True,
        stock_quantity__gt = 0
    ).count()

    return Response({
        'branch': {
            'id': branch.id,
            'branch_name': branch.branch_name,
            'address': branch.address,
            'phone_number': branch.phone_number,
            'is_active': branch.is_active,
        },
        'orders': {
            'total': total_orders,
            'pending': pending_orders,
            'packed': packed_orders,
            'out_for_delivery': out_for_delivery,
            'ready_for_pickup': ready_for_pickup,
            'completed': completed_orders,
            'cancelled': cancelled_orders,
        },
        'revenue': {
            'total': str(total_revenue),
            'today': str(todays_revenue),
            'this_month': str(monthly_revenue),
        },
        'products': {
            'total': total_products,
            'available': available_products,
            'low_stock_count': low_stock.count(),
        },
        'recent_orders': recent_orders_data,
        'low_stock_products': low_stock_data,
    }, status = 200)


# ══════════════════════════════════════════════════════
# CUSTOMER DASHBOARD
# ══════════════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([IsCustomer])
def CustomerDashboard(request):
    user = request.user

    try:
        profile = user.customer_profile
    except Exception:
        return Response({'error': 'Customer profile not found'}, status = 404)

    # ── Order stats ──
    customer_orders = Order.objects.filter(customer = user)
    total_orders = customer_orders.count()
    pending_orders = customer_orders.filter(status = 'placed').count()
    completed_orders = customer_orders.filter(status = 'completed').count()
    cancelled_orders = customer_orders.filter(status = 'cancelled').count()

    # ── Total spent ──
    total_spent = customer_orders.filter(
        status = 'completed'
    ).aggregate(total = Sum('total_amount'))['total'] or 0

    # ── Cart summary ──
    cart_data = {}
    if hasattr(user, 'cart'):
        cart = user.cart
        cart_items = cart.items.select_related('branch_product__product')
        cart_total = sum(item.subtotal for item in cart_items)
        cart_data = {
            'branch': cart.branch.branch_name if cart.branch else None,
            'item_count': cart_items.count(),
            'total': str(cart_total),
            'items': [
                {
                    'product': item.branch_product.product.product_name,
                    'quantity': item.quantity,
                    'subtotal': str(item.subtotal),
                }
                for item in cart_items
            ]
        }

    return Response({
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'phone_number': user.phone_number,
        },
        'profile': {
            'first_name': profile.first_name,
            'last_name': profile.last_name,
            'default_delivery_address': profile.default_delivery_address,
        },
        'orders': {
            'total': total_orders,
            'pending': pending_orders,
            'completed': completed_orders,
            'cancelled': cancelled_orders,
        },
        'total_spent': str(total_spent),
        'cart': cart_data,
    }, status = 200)


# ══════════════════════════════════════════════════════
# CUSTOMER ORDER HISTORY
# ══════════════════════════════════════════════════════

class CustomerOrderHistory(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsCustomer]

    def get_queryset(self):
        return (
            Order.objects
            .filter(customer = self.request.user)
            .select_related('branch', 'customer')
            .prefetch_related('items__branch_product__product')
            .order_by('-created_at')
        )