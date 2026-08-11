from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from accounts.permissions import IsCustomer, IsAdminOrBranchManager
from products.models import BranchProduct
from .models import LoyaltyAccount, Promotion

# Create your views here.
# ======================================================
# CUSTOMER - LOYALTY ACCOUNT
# ======================================================

@api_view(['GET'])
@permission_classes([IsCustomer])
def MyLoyaltyAccount(request):
    account, _ = LoyaltyAccount.objects.get_or_create(customer = request.user)
    return Response({
        'points_balance': account.points_balance,
        'points_value_kes': account.points_balance,  # 1 point = KES 1 when redeemed
        'lifetime_points_earned': account.lifetime_points_earned,
    }, status = 200)


@api_view(['GET'])
@permission_classes([IsCustomer])
def MyLoyaltyTransactions(request):
    account, _ = LoyaltyAccount.objects.get_or_create(customer = request.user)
    transactions = account.transactions.all()[:50]

    data = [{
        'id': t.id,
        'order_id': t.order.id if t.order else None,
        'type': t.transaction_type,
        'points': t.points,
        'created_at': t.created_at,
    } for t in transactions]

    return Response(data, status = 200)


# ======================================================
# PROMOTIONS - ADMIN / BRANCH MANAGER
# ======================================================

@api_view(['POST'])
@permission_classes([IsAdminOrBranchManager])
def CreatePromotion(request):
    branch_product_id = request.data.get('branch_product_id')
    discounted_price = request.data.get('discounted_price')
    start_datetime = request.data.get('start_datetime')
    end_datetime = request.data.get('end_datetime')

    if not all([branch_product_id, discounted_price, start_datetime, end_datetime]):
        return Response({
            'error': 'branch_product_id, discounted_price, start_datetime and end_datetime are required'
        }, status = 400)

    try:
        branch_product = BranchProduct.objects.select_related('branch', 'product').get(id = branch_product_id)
    except BranchProduct.DoesNotExist:
        return Response({'error': 'Branch product not found'}, status = 404)

    # Branch managers may only run promotions on their own branch's products
    if request.user.role == 'branch_manager':
        try:
            branch = request.user.managed_branch
        except Exception:
            return Response({'error': 'You are not assigned to any branch'}, status = 404)
        if branch_product.branch != branch:
            return Response({'error': 'You can only create promotions for your own branch'}, status = 403)

    try:
        discounted_price = float(discounted_price)
    except (TypeError, ValueError):
        return Response({'error': 'discounted_price must be a number'}, status = 400)

    if discounted_price <= 0:
        return Response({'error': 'discounted_price must be greater than 0'}, status = 400)

    if discounted_price >= float(branch_product.price):
        return Response({
            'error': f'discounted_price must be less than the current price (KES {branch_product.price})'
        }, status = 400)

    if end_datetime <= start_datetime:
        return Response({'error': 'end_datetime must be after start_datetime'}, status = 400)

    promo = Promotion.objects.create(
        branch_product = branch_product,
        discounted_price = discounted_price,
        start_datetime = start_datetime,
        end_datetime = end_datetime,
        created_by = request.user,
    )

    return Response({
        'message': 'Promotion created successfully',
        'promotion': {
            'id': promo.id,
            'branch_product_id': branch_product.id,
            'product_name': branch_product.product.product_name,
            'branch': branch_product.branch.branch_name,
            'original_price': str(branch_product.price),
            'discounted_price': str(promo.discounted_price),
            'start_datetime': promo.start_datetime,
            'end_datetime': promo.end_datetime,
            'is_active': promo.is_active,
        }
    }, status = 201)


@api_view(['GET'])
@permission_classes([IsAdminOrBranchManager])
def ListPromotions(request):
    promotions = Promotion.objects.select_related('branch_product__product', 'branch_product__branch')

    if request.user.role == 'branch_manager':
        try:
            branch = request.user.managed_branch
        except Exception:
            return Response({'error': 'You are not assigned to any branch'}, status = 404)
        promotions = promotions.filter(branch_product__branch = branch)
    else:
        branch_filter = request.query_params.get('branch')
        if branch_filter:
            promotions = promotions.filter(branch_product__branch_id = branch_filter)

    data = []
    for p in promotions:
        data.append({
            'id': p.id,
            'branch_product_id': p.branch_product.id,
            'product_name': p.branch_product.product.product_name,
            'branch': p.branch_product.branch.branch_name,
            'original_price': str(p.branch_product.price),
            'discounted_price': str(p.discounted_price),
            'start_datetime': p.start_datetime,
            'end_datetime': p.end_datetime,
            'is_active': p.is_active,
            'is_currently_active': p.is_currently_active(),
        })

    return Response(data, status = 200)


@api_view(['PUT'])
@permission_classes([IsAdminOrBranchManager])
def UpdatePromotion(request, promo_id):
    try:
        promo = Promotion.objects.select_related('branch_product__branch').get(id = promo_id)
    except Promotion.DoesNotExist:
        return Response({'error': 'Promotion not found'}, status = 404)

    if request.user.role == 'branch_manager':
        try:
            branch = request.user.managed_branch
        except Exception:
            return Response({'error': 'You are not assigned to any branch'}, status = 404)
        if promo.branch_product.branch != branch:
            return Response({'error': 'You can only update promotions for your own branch'}, status = 403)

    discounted_price = request.data.get('discounted_price')
    start_datetime = request.data.get('start_datetime')
    end_datetime = request.data.get('end_datetime')
    is_active = request.data.get('is_active')

    if discounted_price is not None:
        try:
            discounted_price = float(discounted_price)
        except (TypeError, ValueError):
            return Response({'error': 'discounted_price must be a number'}, status = 400)
        if discounted_price <= 0 or discounted_price >= float(promo.branch_product.price):
            return Response({
                'error': f'discounted_price must be greater than 0 and less than KES {promo.branch_product.price}'
            }, status = 400)
        promo.discounted_price = discounted_price

    if start_datetime:
        promo.start_datetime = start_datetime
    if end_datetime:
        promo.end_datetime = end_datetime

    if promo.end_datetime <= promo.start_datetime:
        return Response({'error': 'end_datetime must be after start_datetime'}, status = 400)

    if is_active is not None:
        promo.is_active = bool(is_active)

    promo.save()

    return Response({'message': 'Promotion updated successfully'}, status = 200)


@api_view(['DELETE'])
@permission_classes([IsAdminOrBranchManager])
def DeletePromotion(request, promo_id):
    try:
        promo = Promotion.objects.select_related('branch_product__branch').get(id = promo_id)
    except Promotion.DoesNotExist:
        return Response({'error': 'Promotion not found'}, status = 404)

    if request.user.role == 'branch_manager':
        try:
            branch = request.user.managed_branch
        except Exception:
            return Response({'error': 'You are not assigned to any branch'}, status = 404)
        if promo.branch_product.branch != branch:
            return Response({'error': 'You can only delete promotions for your own branch'}, status = 403)

    promo.delete()
    return Response({'message': 'Promotion deleted'}, status = 200)


# ======================================================
# ACTIVE PROMOTIONS - CUSTOMER-FACING (for Shop browsing)
# ======================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def ActivePromotions(request):
    branch_id = request.query_params.get('branch')
    if not branch_id:
        return Response({'error': 'branch is required'}, status = 400)

    now = timezone.now()
    promotions = Promotion.objects.select_related('branch_product__product').filter(
        branch_product__branch_id = branch_id,
        is_active = True,
        start_datetime__lte = now,
        end_datetime__gte = now,
    )

    data = [{
        'branch_product_id': p.branch_product.id,
        'product_name': p.branch_product.product.product_name,
        'original_price': str(p.branch_product.price),
        'discounted_price': str(p.discounted_price),
        'end_datetime': p.end_datetime,
    } for p in promotions]

    return Response(data, status = 200)
