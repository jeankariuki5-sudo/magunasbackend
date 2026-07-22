from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from accounts.permissions import IsAdmin, IsBranchManager
from orders.models import Order, OrderItem
from branches.models import Branch


# ══════════════════════════════════════════════════════
# ADMIN ANALYTICS
# ══════════════════════════════════════════════════════

# ─── REVENUE PER BRANCH ───────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAdmin])
def RevenuePerBranch(request):
    """
    Optional filters: ?start_date=2026-01-01&end_date=2026-12-31
    """
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')

    orders = Order.objects.filter(status = 'completed')

    if start_date:
        orders = orders.filter(created_at__date__gte = start_date)
    if end_date:
        orders = orders.filter(created_at__date__lte = end_date)

    branches = Branch.objects.filter(is_active = True)

    data = []
    for branch in branches:
        branch_orders = orders.filter(branch = branch)
        total_revenue = branch_orders.aggregate(
            total = Sum('total_amount')
        )['total'] or 0

        total_orders = branch_orders.count()
        delivery_orders = branch_orders.filter(fulfillment_type = 'delivery').count()
        pickup_orders = branch_orders.filter(fulfillment_type = 'pickup').count()

        data.append({
            'branch_id': branch.id,
            'branch_name': branch.branch_name,
            'total_revenue': str(total_revenue),
            'total_orders': total_orders,
            'delivery_orders': delivery_orders,
            'pickup_orders': pickup_orders,
        })

    # Sort by revenue — highest first
    data.sort(key = lambda x: float(x['total_revenue']), reverse = True)

    total_all_branches = sum(float(d['total_revenue']) for d in data)

    return Response({
        'total_revenue_all_branches': str(round(total_all_branches, 2)),
        'branches': data,
    }, status = 200)


# ─── TOP SELLING PRODUCTS ─────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAdmin])
def TopSellingProducts(request):
    """
    Optional: ?limit=10&start_date=2026-01-01&end_date=2026-12-31
    """
    limit = int(request.query_params.get('limit', 10))
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')

    order_items = OrderItem.objects.filter(
        order__status = 'completed'
    ).select_related('branch_product__product')

    if start_date:
        order_items = order_items.filter(order__created_at__date__gte = start_date)
    if end_date:
        order_items = order_items.filter(order__created_at__date__lte = end_date)

    product_sales = {}
    for item in order_items:
        product_name = item.branch_product.product.product_name
        product_id = item.branch_product.product.id

        if product_id not in product_sales:
            product_sales[product_id] = {
                'product_id': product_id,
                'product_name': product_name,
                'total_quantity_sold': 0,
                'total_revenue': 0,
            }

        product_sales[product_id]['total_quantity_sold'] += item.quantity
        product_sales[product_id]['total_revenue'] += float(item.unit_price * item.quantity)

    sorted_products = sorted(
        product_sales.values(),
        key = lambda x: x['total_quantity_sold'],
        reverse = True
    )[:limit]

    for p in sorted_products:
        p['total_revenue'] = str(round(p['total_revenue'], 2))

    return Response({
        'top_selling_products': sorted_products,
    }, status = 200)


# ─── ORDERS BY DATE ───────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAdmin])
def OrdersByDate(request):
    """
    Optional: ?period=daily&start_date=2026-01-01&end_date=2026-12-31
    period options: daily, weekly, monthly
    """
    period = request.query_params.get('period', 'daily')
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')

    if not start_date:
        start_date = (timezone.now() - timedelta(days = 30)).date()
    if not end_date:
        end_date = timezone.now().date()

    orders = Order.objects.filter(
        created_at__date__gte = start_date,
        created_at__date__lte = end_date,
    ).order_by('created_at')

    grouped = {}
    for order in orders:
        if period == 'daily':
            key = str(order.created_at.date())
        elif period == 'weekly':
            week = order.created_at.isocalendar()
            key = f"{week[0]}-W{week[1]}"
        elif period == 'monthly':
            key = order.created_at.strftime('%Y-%m')
        else:
            key = str(order.created_at.date())

        if key not in grouped:
            grouped[key] = {
                'period': key,
                'total_orders': 0,
                'completed_orders': 0,
                'cancelled_orders': 0,
                'total_revenue': 0,
            }

        grouped[key]['total_orders'] += 1
        if order.status == 'completed':
            grouped[key]['completed_orders'] += 1
            grouped[key]['total_revenue'] += float(order.total_amount)
        if order.status == 'cancelled':
            grouped[key]['cancelled_orders'] += 1

    result = []
    for key, value in grouped.items():
        value['total_revenue'] = str(round(value['total_revenue'], 2))
        result.append(value)

    return Response({
        'period': period,
        'start_date': str(start_date),
        'end_date': str(end_date),
        'data': result,
    }, status = 200)


# ══════════════════════════════════════════════════════
# BRANCH MANAGER ANALYTICS
# ══════════════════════════════════════════════════════

# ─── BRANCH REVENUE ───────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsBranchManager])
def BranchRevenue(request):
    """
    Optional: ?start_date=2026-01-01&end_date=2026-12-31
    """
    try:
        branch = request.user.managed_branch
    except Exception:
        return Response({'error': 'You are not assigned to any branch'}, status = 404)

    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')

    today = timezone.now().date()
    month_start = today.replace(day = 1)
    week_start = today - timedelta(days = 7)

    orders = Order.objects.filter(branch = branch, status = 'completed')

    if start_date:
        orders = orders.filter(created_at__date__gte = start_date)
    if end_date:
        orders = orders.filter(created_at__date__lte = end_date)

    total_revenue = orders.aggregate(
        total = Sum('total_amount')
    )['total'] or 0

    today_revenue = Order.objects.filter(
        branch = branch,
        status = 'completed',
        created_at__date = today
    ).aggregate(total = Sum('total_amount'))['total'] or 0

    weekly_revenue = Order.objects.filter(
        branch = branch,
        status = 'completed',
        created_at__date__gte = week_start
    ).aggregate(total = Sum('total_amount'))['total'] or 0

    monthly_revenue = Order.objects.filter(
        branch = branch,
        status = 'completed',
        created_at__date__gte = month_start
    ).aggregate(total = Sum('total_amount'))['total'] or 0

    total_orders = Order.objects.filter(branch = branch).count()
    completed_orders = Order.objects.filter(branch = branch, status = 'completed').count()
    cancelled_orders = Order.objects.filter(branch = branch, status = 'cancelled').count()
    pending_orders = Order.objects.filter(branch = branch, status = 'placed').count()

    return Response({
        'branch': branch.branch_name,
        'revenue': {
            'total': str(total_revenue),
            'today': str(today_revenue),
            'this_week': str(weekly_revenue),
            'this_month': str(monthly_revenue),
        },
        'orders': {
            'total': total_orders,
            'completed': completed_orders,
            'cancelled': cancelled_orders,
            'pending': pending_orders,
        }
    }, status = 200)


# ─── BRANCH TOP PRODUCTS ──────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsBranchManager])
def BranchTopProducts(request):
    """
    Optional: ?limit=10&start_date=2026-01-01&end_date=2026-12-31
    """
    try:
        branch = request.user.managed_branch
    except Exception:
        return Response({'error': 'You are not assigned to any branch'}, status = 404)

    limit = int(request.query_params.get('limit', 10))
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')

    order_items = OrderItem.objects.filter(
        order__branch = branch,
        order__status = 'completed'
    ).select_related('branch_product__product')

    if start_date:
        order_items = order_items.filter(order__created_at__date__gte = start_date)
    if end_date:
        order_items = order_items.filter(order__created_at__date__lte = end_date)

    product_sales = {}
    for item in order_items:
        product_name = item.branch_product.product.product_name
        product_id = item.branch_product.product.id

        if product_id not in product_sales:
            product_sales[product_id] = {
                'product_id': product_id,
                'product_name': product_name,
                'total_quantity_sold': 0,
                'total_revenue': 0,
            }

        product_sales[product_id]['total_quantity_sold'] += item.quantity
        product_sales[product_id]['total_revenue'] += float(item.unit_price * item.quantity)

    sorted_products = sorted(
        product_sales.values(),
        key = lambda x: x['total_quantity_sold'],
        reverse = True
    )[:limit]

    for p in sorted_products:
        p['total_revenue'] = str(round(p['total_revenue'], 2))

    return Response({
        'branch': branch.branch_name,
        'top_products': sorted_products,
    }, status = 200)