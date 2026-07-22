from django.shortcuts import render
from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from accounts.models import ActivityLog
from accounts.utils import GetClientIP
from django_ratelimit.decorators import ratelimit
from django_ratelimit.exceptions import Ratelimited
from django.http import JsonResponse

from accounts.permissions import IsAdmin, IsBranchManager, IsCustomer, IsAdminOrBranchManager
from branches.models import Branch, DeliveryZone
from products.models import BranchProduct
from .models import Cart, CartItem, Order, OrderItem

def Handler403(request, exception = None):
    # NEW: Return 429 for rate limit, 403 for everything else
    if isinstance(exception, Ratelimited):
        return JsonResponse({
            'error': 'Too many requests. Please slow down and try again shortly.'
        }, status = 429)

    return JsonResponse({
        'error': 'Permission denied.'
    }, status = 403)

# Create your views here.
# ======================================================
# CART VIEWS
# ======================================================

# ======================================================
# View cart
# ======================================================
@api_view(['GET'])
@permission_classes([IsCustomer])
def ViewCart(request):
    try:
        cart = Cart.objects.get(customer = request.user)
    except Cart.DoesNotExist:
        return Response({
            'branch': None,
            'item_count': 0,
            'items': [],
            'total': '0.00'
        }, status = 200)

    items = cart.items.select_related(
        'branch_product__product',
        'branch_product__branch'
    )

    items_data = []
    for item in items:
        items_data.append({
            'id': item.id,
            'branch_product_id': item.branch_product.id,
            'product_name': item.branch_product.product.product_name,
            'price': str(item.branch_product.price),
            'quantity': item.quantity,
            'subtotal': str(item.subtotal),
            'in_stock': item.branch_product.in_stock,
            'stock_quantity': item.branch_product.stock_quantity,
        })

    cart_total = sum(item.subtotal for item in items)

    return Response({
        'cart_id': cart.id,
        'branch': {
            'id': cart.branch.id,
            'branch_name': cart.branch.branch_name,
        } if cart.branch else None,
        'item_count': items.count(),
        'items': items_data,
        'total': str(cart_total),
    }, status = 200)


# ==================================================
# Add to cart 
# ==================================================

@api_view(['POST'])
@permission_classes([IsCustomer])
@ratelimit(key = 'user', rate = '30/m', block = False)
def AddToCart(request):
    branch_product_id = request.data.get('branch_product_id')
    quantity = int(request.data.get('quantity', 1))

    if getattr(request, 'limited', False):
        return Response({'error': 'Too many requests. Please slow down.'}, status = 429)

    if not branch_product_id:
        return Response({'error': 'branch_product_id is required'}, status = 400)

    if quantity < 1:
        return Response({'error': 'Quantity must be at least 1'}, status = 400)
    
    if quantity > 100:
        return Response({'error': 'Maximum quantity per item is 100'}, status = 400)

    # Validate branch product
    try:
        branch_product = BranchProduct.objects.select_related(
            'product', 'branch'
        ).get(id = branch_product_id, is_available = True)
    except BranchProduct.DoesNotExist:
        return Response({'error': 'Product not found or unavailable'}, status = 404)
    

    # Check total quantity in cart + new quantity doesn't exceed stock
    cart_check = Cart.objects.filter(customer = request.user).first()
    existing_cart_item = None
    if cart_check:
        existing_cart_item = CartItem.objects.filter(
            cart = cart_check,
            branch_product = branch_product
        ).first()

    current_cart_quantity = existing_cart_item.quantity if existing_cart_item else 0
    total_requested = current_cart_quantity + quantity

    if branch_product.stock_quantity < total_requested:
        return Response({
            'error': f'Not enough stock. Only {branch_product.stock_quantity} available '
                     f'and you already have {current_cart_quantity} in your cart.'
        }, status = 400)

    # Get or create cart
    cart, created = Cart.objects.get_or_create(
        customer = request.user,
        defaults = {'branch': branch_product.branch}
    )

    # Enforce single branch per cart
    if cart.branch != branch_product.branch:
        return Response({
            'error': f'Your cart contains items from {cart.branch.branch_name}. '
                     f'Clear your cart before adding items from a different branch.'
        }, status = 400)

    # Add or update cart item
    cart_item, item_created = CartItem.objects.get_or_create(
        cart = cart,
        branch_product = branch_product,
        defaults = {'quantity': quantity}
    )

    if not item_created:
        # Item exists — add to quantity
        new_quantity = cart_item.quantity + quantity
        if branch_product.stock_quantity < new_quantity:
            return Response({
                'error': f'Not enough stock. Only {branch_product.stock_quantity} available.'
            }, status = 400)
        cart_item.quantity = new_quantity
        cart_item.save()

    return Response({
        'message': 'Item added to cart successfully',
        'item': {
            'id': cart_item.id,
            'product_name': branch_product.product.product_name,
            'price': str(branch_product.price),
            'quantity': cart_item.quantity,
            'subtotal': str(cart_item.subtotal),
        }
    }, status = 200)


# =================================================
#  Update cart item
# =================================================

@api_view(['PUT'])
@permission_classes([IsCustomer])
def UpdateCartItem(request, cart_item_id):
    quantity = request.data.get('quantity')

    if not quantity:
        return Response({'error': 'quantity is required'}, status = 400)

    quantity = int(quantity)
    if quantity < 1:
        return Response({'error': 'Quantity must be at least 1'}, status = 400)
    
    if quantity > 100:
        return Response({'error': 'Maximum quantity per item is 100'}, status = 400)

    try:
        cart_item = CartItem.objects.select_related(
            'cart__customer',
            'branch_product'
        ).get(id = cart_item_id, cart__customer = request.user)
    except CartItem.DoesNotExist:
        return Response({'error': 'Cart item not found'}, status=404)

    if cart_item.branch_product.stock_quantity < quantity:
        return Response({
            'error': f'Not enough stock. Only {cart_item.branch_product.stock_quantity} available.'
        }, status = 400)

    cart_item.quantity = quantity
    cart_item.save()

    return Response({
        'message': 'Cart item updated successfully',
        'item': {
            'id': cart_item.id,
            'product_name': cart_item.branch_product.product.product_name,
            'quantity': cart_item.quantity,
            'subtotal': str(cart_item.subtotal),
        }
    }, status = 200)


# =======================================================
#  Remove cart item
# =======================================================
@api_view(['DELETE'])
@permission_classes([IsCustomer])
def RemoveCartItem(request, cart_item_id):
    try:
        cart_item = CartItem.objects.get(
            id = cart_item_id,
            cart__customer = request.user
        )
    except CartItem.DoesNotExist:
        return Response({'error': 'Cart item not found'}, status = 404)

    product_name = cart_item.branch_product.product.product_name
    cart_item.delete()

    return Response({'message': f'{product_name} removed from cart'}, status = 200)


# ===================================================
# Clear cart
# ===================================================

@api_view(['DELETE'])
@permission_classes([IsCustomer])
def ClearCart(request):
    try:
        cart = Cart.objects.get(customer=request.user)
    except Cart.DoesNotExist:
        return Response({'error': 'Cart is already empty'}, status = 400)

    cart.items.all().delete()
    cart.delete()

    return Response({'message': 'Cart cleared successfully'}, status = 200)


# ======================================================
# ORDER VIEWS
# ======================================================

# ======================================================
#  Place order (checkout)
# ======================================================

@api_view(['POST'])
@permission_classes([IsCustomer])
@ratelimit(key = 'ip', rate = '10/m', block = False)
@transaction.atomic
def PlaceOrder(request):
    fulfillment_type = request.data.get('fulfillment_type')  # delivery or pickup
    delivery_address = request.data.get('delivery_address', '')
    delivery_zone_id = request.data.get('delivery_zone_id')

    if getattr(request, 'limited', False):
        return Response({'error': 'Too many requests. Please slow down.'}, status = 429)

    if not fulfillment_type:
        return Response({'error': 'fulfillment_type is required (delivery or pickup)'}, status = 400)

    if fulfillment_type not in ['delivery', 'pickup']:
        return Response({'error': 'fulfillment_type must be delivery or pickup'}, status = 400)

    if fulfillment_type == 'delivery' and not delivery_address:
        return Response({'error': 'delivery_address is required for delivery orders'}, status = 400)

    if fulfillment_type == 'delivery' and not delivery_zone_id:
        return Response({'error': 'delivery_zone_id is required for delivery orders'}, status = 400)

    # Get cart
    try:
        cart = Cart.objects.get(customer = request.user)
    except Cart.DoesNotExist:
        return Response({'error': 'Your cart is empty'}, status = 400)

    cart_items = cart.items.select_related('branch_product__product')

    if not cart_items.exists():
        return Response({'error': 'Your cart is empty'}, status = 400)

    # Validate delivery zone
    delivery_zone = None
    delivery_fee = 0

    if fulfillment_type == 'delivery':
        try:
            delivery_zone = DeliveryZone.objects.get(
                id = delivery_zone_id,
                branch = cart.branch,
                is_active =  True
            )
            delivery_fee = delivery_zone.delivery_fee
        except DeliveryZone.DoesNotExist:
            return Response({'error': 'Invalid or inactive delivery zone for this branch'}, status = 404)

    # Validate stock and calculate total
    items_total = 0
    for item in cart_items:
        bp = item.branch_product
        if bp.stock_quantity < item.quantity:
            return Response({
                'error': f'Not enough stock for {bp.product.product_name}. '
                         f'Only {bp.stock_quantity} available.'
            }, status = 400)
        items_total += bp.price * item.quantity

    total_amount = items_total + delivery_fee

    # Create order
    order = Order.objects.create(
        customer = request.user,
        branch = cart.branch,
        fulfillment_type = fulfillment_type,
        delivery_zone = delivery_zone,
        delivery_address = delivery_address,
        total_amount = total_amount,
        delivery_fee = delivery_fee,
        status = 'placed'
    )

    ActivityLog.objects.create(
        user = request.user,
        action = 'order_placed',
        ip_address = GetClientIP(request),
        detail = f'Order #{order.id} placed at {order.branch.branch_name}'
    )

    # Create order items and decrement stock atomically
    for item in cart_items:
        bp = item.branch_product
        OrderItem.objects.create(
            order = order,
            branch_product = bp,
            quantity = item.quantity,
            unit_price = bp.price  # snapshot price at time of order
        )
        # Decrement stock
        bp.stock_quantity -= item.quantity
        bp.save()

    # Clear cart after order placed
    cart.items.all().delete()
    cart.delete()

    return Response({
        'message': 'Order placed successfully',
        'order': {
            'id': order.id,
            'branch': order.branch.branch_name,
            'fulfillment_type': order.fulfillment_type,
            'delivery_address': order.delivery_address,
            'delivery_zone': delivery_zone.zone_name if delivery_zone else None,
            'delivery_fee': str(order.delivery_fee),
            'total_amount': str(order.total_amount),
            'status': order.status,
            'created_at': order.created_at,
        }
    }, status = 201)


# ===============================================
# My orders(customer) 
# ===============================================
@api_view(['GET'])
@permission_classes([IsCustomer])
def MyOrders(request):
    orders = Order.objects.filter(
        customer = request.user
    ).select_related('branch', 'delivery_zone').order_by('-created_at')

    # Filter by status
    status_filter = request.query_params.get('status')
    if status_filter:
        orders = orders.filter(status = status_filter)

    data = []
    for order in orders:
        items = order.items.select_related('branch_product__product')
        data.append({
            'id': order.id,
            'branch': order.branch.branch_name,
            'fulfillment_type': order.fulfillment_type,
            'delivery_address': order.delivery_address,
            'delivery_zone': order.delivery_zone.zone_name if order.delivery_zone else None,
            'delivery_fee': str(order.delivery_fee),
            'total_amount': str(order.total_amount),
            'status': order.status,
            'created_at': order.created_at,
            'items': [
                {
                    'product_name': item.branch_product.product.product_name,
                    'quantity': item.quantity,
                    'unit_price': str(item.unit_price),
                    'subtotal': str(item.subtotal),
                }
                for item in items
            ]
        })

    return Response(data, status = 200)


# ========================================================
#  Get single order (customer) 
# ========================================================
@api_view(['GET'])
@permission_classes([IsCustomer])
def GetMyOrder(request, order_id):
    try:
        order = Order.objects.select_related(
            'branch', 'delivery_zone'
        ).get(id = order_id, customer = request.user)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status = 404)

    items = order.items.select_related('branch_product__product')

    return Response({
        'id': order.id,
        'branch': order.branch.branch_name,
        'fulfillment_type': order.fulfillment_type,
        'delivery_address': order.delivery_address,
        'delivery_zone': order.delivery_zone.zone_name if order.delivery_zone else None,
        'delivery_fee': str(order.delivery_fee),
        'total_amount': str(order.total_amount),
        'status': order.status,
        'created_at': order.created_at,
        'updated_at': order.updated_at,
        'items': [
            {
                'product_name': item.branch_product.product.product_name,
                'quantity': item.quantity,
                'unit_price': str(item.unit_price),
                'subtotal': str(item.subtotal),
            }
            for item in items
        ]
    }, status = 200)


# ===================================================
#  Cancel order (customer) 
# ===================================================
@api_view(['POST'])
@permission_classes([IsCustomer])
@ratelimit(key = 'ip', rate = '10/h', block = False)
@transaction.atomic
def CancelOrder(request, order_id):

    if getattr(request, 'limited', False):
        return Response({'error': 'Too many requests. Please slow down.'}, status = 429)

    try:
        order = Order.objects.get(id = order_id, customer = request.user)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status = 404)

    if order.status == 'cancelled':
        return Response({'error': 'Order is already cancelled'}, status = 400)

    if order.status == 'completed':
        return Response({'error': 'Completed orders cannot be cancelled'}, status = 400)
    
    # Prevent cancellation if payment was successful
    if hasattr(order, 'payment') and order.payment.status == 'success':
        return Response({
            'error': 'Cannot cancel a paid order. Contact support for a refund.'
        }, status = 400)


    # Restore stock for each item
    order_items = order.items.select_related('branch_product')
    for item in order_items:
        bp = item.branch_product
        bp.stock_quantity += item.quantity
        bp.save()

    order.status = 'cancelled'
    order.save()

    ActivityLog.objects.create(
        user = request.user,
        action = 'order_cancelled',
        ip_address = GetClientIP(request),
        detail = f'Order #{order.id} cancelled'
    )

    return Response({
        'message': f'Order #{order.id} cancelled successfully',
        'order_id': order.id,
        'status': order.status,
    }, status = 200)


# ======================================================
# BRANCH MANAGER ORDER VIEWS
# ======================================================

# ======================================================
#  List branch orders (branch manager)
# ======================================================
@api_view(['GET'])
@permission_classes([IsBranchManager])
def BranchOrders(request):
    try:
        branch = request.user.managed_branch
    except Exception:
        return Response({'error': 'You are not assigned to any branch'}, status = 404)

    orders = Order.objects.filter(
        branch=branch
    ).select_related('customer', 'delivery_zone').order_by('-created_at')

    # Filter by status
    status_filter = request.query_params.get('status')
    if status_filter:
        orders = orders.filter(status = status_filter)

    # Filter by fulfillment type
    fulfillment_filter = request.query_params.get('fulfillment_type')
    if fulfillment_filter:
        orders = orders.filter(fulfillment_type = fulfillment_filter)

    data = []
    for order in orders:
        items = order.items.select_related('branch_product__product')
        data.append({
            'id': order.id,
            'customer': order.customer.username,
            'fulfillment_type': order.fulfillment_type,
            'delivery_address': order.delivery_address,
            'delivery_zone': order.delivery_zone.zone_name if order.delivery_zone else None,
            'delivery_fee': str(order.delivery_fee),
            'total_amount': str(order.total_amount),
            'status': order.status,
            'created_at': order.created_at,
            'items': [
                {
                    'product_name': item.branch_product.product.product_name,
                    'quantity': item.quantity,
                    'unit_price': str(item.unit_price),
                    'subtotal': str(item.subtotal),
                }
                for item in items
            ]
        })

    return Response(data, status=200)


# ======================================================
#  Update order status (admin or branch manager)
# ======================================================
@api_view(['PUT'])
@permission_classes([IsAdminOrBranchManager])
def UpdateOrderStatus(request, order_id):
    new_status = request.data.get('status')

    if not new_status:
        return Response({'error': 'status is required'}, status = 400)

    valid_statuses = ['placed', 'packed', 'out_for_delivery', 'ready_for_pickup', 'completed', 'cancelled']
    if new_status not in valid_statuses:
        return Response({
            'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
        }, status = 400)

    # Fetch order
    try:
        order = Order.objects.get(id = order_id)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status = 404)

    # Prevent branch manager from updating orders from other branches
    if request.user.role == 'branch_manager':
        try:
            branch = request.user.managed_branch
        except Exception:
            return Response({'error': 'You are not assigned to any branch'}, status = 404)
        if order.branch != branch:
            return Response({'error': 'You can only update orders from your own branch'}, status = 403)

    if order.status == 'completed':
        return Response({'error': 'Completed orders cannot be updated'}, status = 400)

    if order.status == 'cancelled':
        return Response({'error': 'Cancelled orders cannot be updated'}, status = 400)

    order.status = new_status
    order.save()

    return Response({
        'message': f'Order #{order.id} status updated to {new_status}',
        'order_id': order.id,
        'status': order.status,
        'updated_at': order.updated_at,
    }, status = 200)


# ======================================================
#  List all orders (admin only) 
# ======================================================
@api_view(['GET'])
@permission_classes([IsAdmin])
def AllOrders(request):
    orders = Order.objects.select_related(
        'customer', 'branch', 'delivery_zone'
    ).order_by('-created_at')

    # Filters
    status_filter = request.query_params.get('status')
    if status_filter:
        orders = orders.filter(status = status_filter)

    branch_filter = request.query_params.get('branch')
    if branch_filter:
        orders = orders.filter(branch_id = branch_filter)

    fulfillment_filter = request.query_params.get('fulfillment_type')
    if fulfillment_filter:
        orders = orders.filter(fulfillment_type = fulfillment_filter)

    data = []
    for order in orders:
        items = order.items.select_related('branch_product__product')
        data.append({
            'id': order.id,
            'customer': order.customer.username,
            'branch': order.branch.branch_name,
            'fulfillment_type': order.fulfillment_type,
            'delivery_address': order.delivery_address,
            'delivery_zone': order.delivery_zone.zone_name if order.delivery_zone else None,
            'delivery_fee': str(order.delivery_fee),
            'total_amount': str(order.total_amount),
            'status': order.status,
            'created_at': order.created_at,
            'items': [
                {
                    'product_name': item.branch_product.product.product_name,
                    'quantity': item.quantity,
                    'unit_price': str(item.unit_price),
                    'subtotal': str(item.subtotal),
                }
                for item in items
            ]
        })

    return Response(data, status = 200)


# =======================================================
#  Get single order (admin or branch manager) 
# =======================================================
@api_view(['GET'])
@permission_classes([IsAdminOrBranchManager])
def GetOrder(request, order_id):
    try:
        if request.user.role == 'branch_manager':
            branch = request.user.managed_branch
            order = Order.objects.select_related(
                'customer', 'branch', 'delivery_zone'
            ).get(id = order_id, branch = branch)
        else:
            order = Order.objects.select_related(
                'customer', 'branch', 'delivery_zone'
            ).get(id = order_id)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status = 404)
    except Exception:
        return Response({'error': 'You are not assigned to any branch'}, status=404)

    items = order.items.select_related('branch_product__product')

    return Response({
        'id': order.id,
        'customer': order.customer.username,
        'branch': order.branch.branch_name,
        'fulfillment_type': order.fulfillment_type,
        'delivery_address': order.delivery_address,
        'delivery_zone': order.delivery_zone.zone_name if order.delivery_zone else None,
        'delivery_fee': str(order.delivery_fee),
        'total_amount': str(order.total_amount),
        'status': order.status,
        'created_at': order.created_at,
        'updated_at': order.updated_at,
        'items': [
            {
                'product_name': item.branch_product.product.product_name,
                'quantity': item.quantity,
                'unit_price': str(item.unit_price),
                'subtotal': str(item.subtotal),
            }
            for item in items
        ]
    }, status = 200)