from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django_ratelimit.decorators import ratelimit
from django_ratelimit.exceptions import Ratelimited

from accounts.permissions import IsCustomer
from orders.models import Order
from .models import Payment
from .mpesa import InitiateSTKPush


def RateLimitedResponse():
    return Response({
        'error': 'Too many requests. Please slow down and try again shortly.'
    }, status = 429)

# Create your views here.
# =================================================================
# Initiate STK push 
# =================================================================
@api_view(['POST'])
@permission_classes([IsCustomer])
@ratelimit(key = 'user', rate = '3/m', block = False)
def InitiatePayment(request, order_id):
    phone_number = request.data.get('phone_number')

    if getattr(request, 'limited', False):
        return RateLimitedResponse()

    if not phone_number:
        return Response({'error': 'phone_number is required'}, status = 400)

    # Get the order
    try:
        order = Order.objects.get(id = order_id, customer = request.user)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status = 404)

    # Check order status
    if order.status == 'cancelled':
        return Response({'error': 'Cannot pay for a cancelled order'}, status = 400)

    if order.status == 'completed':
        return Response({'error': 'Order is already paid and completed'}, status = 400)
    
    # Confirm amount matches order total
    if float(request.data.get('amount', order.total_amount)) != float(order.total_amount):
        return Response({'error': 'Payment amount does not match order total'}, status = 400)

    # Check if payment already exists and succeeded
    if hasattr(order, 'payment') and order.payment.status == 'success':
        return Response({'error': 'Order is already paid'}, status = 400)

    # Initiate STK push
    result, error = InitiateSTKPush(
        phone_number = phone_number,
        amount = order.total_amount,
        order_id = order.id
    )

    if error:
        return Response({'error': error}, status = 500)

    if result.get('ResponseCode') != '0':
        return Response({
            'error': result.get('ResponseDescription', 'STK push failed')
        }, status = 400)

    # Save or update payment record
    payment, created = Payment.objects.update_or_create(
        order = order,
        defaults = {
            'phone_number': phone_number,
            'amount': order.total_amount,
            'mpesa_checkout_request_id': result.get('CheckoutRequestID'),
            'status': 'pending',
        }
    )

    return Response({
        'message': 'STK push sent successfully. Enter your M-Pesa PIN to complete payment.',
        'checkout_request_id': result.get('CheckoutRequestID'),
        'merchant_request_id': result.get('MerchantRequestID'),
        'order_id': order.id,
        'amount': str(order.total_amount),
        'phone_number': phone_number,
    }, status = 200)


# =====================================================================
# Mpesa callback
# =====================================================================
@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def MpesaCallback(request):
    """
    Safaricom sends payment result here.
    This endpoint must be publicly accessible.
    """
    try:
        data = request.data
        stk_callback = data['Body']['stkCallback']

        checkout_request_id = stk_callback.get('CheckoutRequestID')
        result_code = stk_callback.get('ResultCode')
        result_desc = stk_callback.get('ResultDesc')

        # Find the payment
        try:
            payment = Payment.objects.get(
                mpesa_checkout_request_id = checkout_request_id
            )
        except Payment.DoesNotExist:
            return Response({'error': 'Payment not found'}, status = 404)

        if result_code == 0:
            # Payment successful
            callback_metadata = stk_callback.get('CallbackMetadata', {})
            items = callback_metadata.get('Item', [])

            # Extract receipt number and amount from callback
            receipt_number = ''
            amount = 0

            for item in items:
                if item.get('Name') == 'MpesaReceiptNumber':
                    receipt_number = item.get('Value', '')
                if item.get('Name') == 'Amount':
                    amount = item.get('Value', 0)

            # Update payment
            payment.status = 'success'
            payment.mpesa_receipt_number = receipt_number
            payment.confirmed_at = timezone.now()
            payment.save()

            # Update order status
            payment.order.status = 'packed'
            payment.order.save()

        else:
            # Payment failed or cancelled
            payment.status = 'failed'
            payment.save()

        return Response({'ResultCode': 0, 'ResultDesc': 'Success'}, status = 200)

    except Exception as e:
        return Response({'error': str(e)}, status = 500)


#=========================================================
# Check payment status
# ========================================================
@api_view(['GET'])
@permission_classes([IsCustomer])
def CheckPaymentStatus(request, order_id):
    try:
        order = Order.objects.get(id = order_id, customer = request.user)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status = 404)

    if not hasattr(order, 'payment'):
        return Response({
            'order_id': order.id,
            'payment_status': 'no payment initiated',
        }, status = 200)

    payment = order.payment

    return Response({
        'order_id': order.id,
        'order_status': order.status,
        'payment_status': payment.status,
        'amount': str(payment.amount),
        'phone_number': payment.phone_number,
        'mpesa_receipt': payment.mpesa_receipt_number if payment.status == 'success' else None,
        'initiated_at': payment.initiated_at,
        'confirmed_at': payment.confirmed_at if payment.status == 'success' else None,
    }, status = 200)


# =======================================================
# List all payments (admin only)
# =======================================================
@api_view(['GET'])
@permission_classes([])
def AllPayments(request):
    from accounts.permissions import IsAdmin
    if not request.user.is_authenticated or not (
        request.user.role == 'admin' or request.user.is_superuser
    ):
        return Response({'error': 'Unauthorized'}, status = 403)

    payments = Payment.objects.select_related(
        'order__customer', 'order__branch'
    ).order_by('-initiated_at')

    status_filter = request.query_params.get('status')
    if status_filter:
        payments = payments.filter(status = status_filter)

    data = []
    for p in payments:
        data.append({
            'id': p.id,
            'order_id': p.order.id,
            'customer': p.order.customer.username,
            'branch': p.order.branch.branch_name,
            'phone_number': p.phone_number,
            'amount': str(p.amount),
            'status': p.status,
            'mpesa_receipt': p.mpesa_receipt_number,
            'initiated_at': p.initiated_at,
            'confirmed_at': p.confirmed_at,
        })

    return Response(data, status = 200)