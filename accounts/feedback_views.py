from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import Feedback
from .permissions import IsAdmin, IsBranchManager, IsCustomer


# ===========================================================
# CUSTOMER FEEDBACK
# ===========================================================

# ===========================================================
# Submit feedback
# ===========================================================
@api_view(['POST'])
@permission_classes([IsCustomer])
def SubmitFeedback(request):
    title = request.data.get('title')
    description = request.data.get('description')
    feedback_type = request.data.get('feedback_type', 'general')
    branch_id = request.data.get('branch_id')
    order_id = request.data.get('order_id')

    if not title or not description:
        return Response({'error': 'title and description are required'}, status = 400)

    if feedback_type not in ['general', 'order', 'branch', 'product']:
        return Response({'error': 'Invalid feedback_type'}, status = 400)

    # Validate branch if provided
    branch = None
    if branch_id:
        from branches.models import Branch
        try:
            branch = Branch.objects.get(id = branch_id)
        except Branch.DoesNotExist:
            return Response({'error': 'Branch not found'}, status = 404)

    # Validate order if provided — must belong to customer
    order = None
    if order_id:
        from orders.models import Order
        try:
            order = Order.objects.get(id = order_id, customer = request.user)
        except Order.DoesNotExist:
            return Response({'error': 'Order not found'}, status = 404)

    feedback = Feedback.objects.create(
        submitted_by = request.user,
        title = title,
        description = description,
        feedback_type = feedback_type,
        branch = branch,
        order = order,
    )

    return Response({
        'message': 'Feedback submitted successfully',
        'feedback': {
            'id': feedback.id,
            'title': feedback.title,
            'description': feedback.description,
            'feedback_type': feedback.feedback_type,
            'branch': branch.branch_name if branch else None,
            'order_id': order.id if order else None,
            'status': feedback.status,
            'created_at': feedback.created_at,
        }
    }, status = 201)



# ===========================================================
# My feedback
# ===========================================================
@api_view(['GET'])
@permission_classes([IsCustomer])
def MyFeedback(request):
    feedback = Feedback.objects.filter(
        submitted_by = request.user
    ).order_by('-created_at')

    status_filter = request.query_params.get('status')
    if status_filter:
        feedback = feedback.filter(status = status_filter)

    data = []
    for f in feedback:
        data.append({
            'id': f.id,
            'title': f.title,
            'description': f.description,
            'feedback_type': f.feedback_type,
            'branch': f.branch.branch_name if f.branch else None,
            'order_id': f.order.id if f.order else None,
            'status': f.status,
            'created_at': f.created_at,
        })

    return Response(data, status = 200)


# ===========================================================
# Get my feedback
# ===========================================================
@api_view(['GET'])
@permission_classes([IsCustomer])
def GetMyFeedback(request, feedback_id):
    try:
        feedback = Feedback.objects.get(id = feedback_id, submitted_by = request.user)
    except Feedback.DoesNotExist:
        return Response({'error': 'Feedback not found'}, status = 404)

    return Response({
        'id': feedback.id,
        'title': feedback.title,
        'description': feedback.description,
        'feedback_type': feedback.feedback_type,
        'branch': feedback.branch.branch_name if feedback.branch else None,
        'order_id': feedback.order.id if feedback.order else None,
        'status': feedback.status,
        'created_at': feedback.created_at,
        'updated_at': feedback.updated_at,
    }, status = 200)



# ===========================================================
# Update my feedback
# ===========================================================
@api_view(['PUT'])
@permission_classes([IsCustomer])
def UpdateMyFeedback(request, feedback_id):
    try:
        feedback = Feedback.objects.get(id = feedback_id, submitted_by = request.user)
    except Feedback.DoesNotExist:
        return Response({'error': 'Feedback not found'}, status = 404)

    if feedback.status != 'pending':
        return Response({'error': 'Only pending feedback can be updated'}, status = 400)

    feedback.title = request.data.get('title', feedback.title)
    feedback.description = request.data.get('description', feedback.description)
    feedback.feedback_type = request.data.get('feedback_type', feedback.feedback_type)
    feedback.save()

    return Response({
        'message': 'Feedback updated successfully',
        'feedback': {
            'id': feedback.id,
            'title': feedback.title,
            'description': feedback.description,
            'feedback_type': feedback.feedback_type,
            'status': feedback.status,
        }
    }, status = 200)



# ===========================================================
# Delete my feedback
# ===========================================================
@api_view(['DELETE'])
@permission_classes([IsCustomer])
def DeleteMyFeedback(request, feedback_id):
    try:
        feedback = Feedback.objects.get(id = feedback_id, submitted_by = request.user)
    except Feedback.DoesNotExist:
        return Response({'error': 'Feedback not found'}, status = 404)

    if feedback.status != 'pending':
        return Response({'error': 'Only pending feedback can be deleted'}, status = 400)

    feedback.delete()
    return Response({'message': 'Feedback deleted successfully'}, status = 200)


# ===========================================================
# BRANCH MANAGER FEEDBACK
# ===========================================================

# ===============================================
# Branch feedback
# ===============================================
@api_view(['GET'])
@permission_classes([IsBranchManager])
def BranchFeedback(request):
    try:
        branch = request.user.managed_branch
    except Exception:
        return Response({'error': 'You are not assigned to any branch'}, status = 404)

    feedback = Feedback.objects.filter(
        branch = branch
    ).select_related('customer', 'order').order_by('-created_at')

    status_filter = request.query_params.get('status')
    if status_filter:
        feedback = feedback.filter(status = status_filter)

    data = []
    for f in feedback:
        data.append({
            'id': f.id,
            'customer': f.sumitted_by.username,
            'title': f.title,
            'description': f.description,
            'feedback_type': f.feedback_type,
            'order_id': f.order.id if f.order else None,
            'status': f.status,
            'created_at': f.created_at,
        })

    return Response(data, status = 200)


# ===============================================
#  Get branch feedback
# ===============================================
@api_view(['GET'])
@permission_classes([IsBranchManager])
def GetBranchFeedback(request, feedback_id):
    try:
        branch = request.user.managed_branch
        feedback = Feedback.objects.select_related(
            'customer', 'order'
        ).get(id = feedback_id, branch = branch)
    except Feedback.DoesNotExist:
        return Response({'error': 'Feedback not found'}, status = 404)
    except Exception:
        return Response({'error': 'You are not assigned to any branch'}, status = 404)

    return Response({
        'id': feedback.id,
        'customer': feedback.submitted_by.username,
        'title': feedback.title,
        'description': feedback.description,
        'feedback_type': feedback.feedback_type,
        'order_id': feedback.order.id if feedback.order else None,
        'status': feedback.status,
        'created_at': feedback.created_at,
        'updated_at': feedback.updated_at,
    }, status = 200)


# ===============================================
# Update status (Branch manager)
# ===============================================
@api_view(['PUT'])
@permission_classes([IsBranchManager])
def UpdateBranchFeedbackStatus(request, feedback_id):
    try:
        branch = request.user.managed_branch
        feedback = Feedback.objects.get(id = feedback_id, branch = branch)
    except Feedback.DoesNotExist:
        return Response({'error': 'Feedback not found'}, status = 404)
    except Exception:
        return Response({'error': 'You are not assigned to any branch'}, status = 404)

    new_status = request.data.get('status')

    if not new_status:
        return Response({'error': 'status is required'}, status = 400)

    if new_status not in ['pending', 'reviewed', 'resolved']:
        return Response({'error': 'status must be pending, reviewed or resolved'}, status = 400)

    feedback.status = new_status
    feedback.save()

    return Response({
        'message': f'Feedback status updated to {new_status}',
        'feedback_id': feedback.id,
        'status': feedback.status,
    }, status = 200)


# ===========================================================
# Manager submit feedback
# ===========================================================
@api_view(['POST'])
@permission_classes([IsBranchManager])
def ManagerSubmitFeedback(request):
    title = request.data.get('title')
    description = request.data.get('description')
    feedback_type = request.data.get('feedback_type', 'general')

    if not title or not description:
        return Response({'error': 'title and description are required'}, status = 400)

    if feedback_type not in ['general', 'order', 'branch', 'product']:
        return Response({'error': 'Invalid feedback_type'}, status = 400)

    try:
        branch = request.user.managed_branch
    except Exception:
        return Response({'error': 'You are not assigned to any branch'}, status = 404)

    feedback = Feedback.objects.create(
        customer = request.user,
        title = title,
        description = description,
        feedback_type = feedback_type,
        branch = branch,
    )

    return Response({
        'message': 'Feedback submitted to admin successfully',
        'feedback': {
            'id': feedback.id,
            'title': feedback.title,
            'description': feedback.description,
            'feedback_type': feedback.feedback_type,
            'branch': branch.branch_name,
            'status': feedback.status,
            'created_at': feedback.created_at,
        }
    }, status = 201)


# ===========================================================
#  ADMIN FEEDBACK
# ===========================================================

# ===============================================
# All feedback
# ===============================================
@api_view(['GET'])
@permission_classes([IsAdmin])
def AllFeedback(request):
    feedback = Feedback.objects.select_related(
        'customer', 'branch', 'order'
    ).order_by('-created_at')

    status_filter = request.query_params.get('status')
    if status_filter:
        feedback = feedback.filter(status = status_filter)

    branch_filter = request.query_params.get('branch')
    if branch_filter:
        feedback = feedback.filter(branch_id = branch_filter)

    type_filter = request.query_params.get('feedback_type')
    if type_filter:
        feedback = feedback.filter(feedback_type = type_filter)

    data = []
    for f in feedback:
        data.append({
            'id': f.id,
            'customer': f.submitted_by.username,
            'branch': f.branch.branch_name if f.branch else None,
            'order_id': f.order.id if f.order else None,
            'title': f.title,
            'description': f.description,
            'feedback_type': f.feedback_type,
            'status': f.status,
            'created_at': f.created_at,
        })

    return Response(data, status = 200)

# ===============================================
# Get feedback
# ===============================================
@api_view(['GET'])
@permission_classes([IsAdmin])
def GetFeedback(request, feedback_id):
    try:
        feedback = Feedback.objects.select_related(
            'customer', 'branch', 'order'
        ).get(id = feedback_id)
    except Feedback.DoesNotExist:
        return Response({'error': 'Feedback not found'}, status = 404)

    return Response({
        'id': feedback.id,
        'customer': feedback.submitted_by.username,
        'branch': feedback.branch.branch_name if feedback.branch else None,
        'order_id': feedback.order.id if feedback.order else None,
        'title': feedback.title,
        'description': feedback.description,
        'feedback_type': feedback.feedback_type,
        'status': feedback.status,
        'created_at': feedback.created_at,
        'updated_at': feedback.updated_at,
    }, status = 200)

# ===============================================
# Admin update feedback status
## ===============================================
@api_view(['PUT'])
@permission_classes([IsAdmin])
def AdminUpdateFeedbackStatus(request, feedback_id):
    try:
        feedback = Feedback.objects.get(id = feedback_id)
    except Feedback.DoesNotExist:
        return Response({'error': 'Feedback not found'}, status = 404)

    new_status = request.data.get('status')

    if not new_status:
        return Response({'error': 'status is required'}, status = 400)

    if new_status not in ['pending', 'reviewed', 'resolved']:
        return Response({'error': 'status must be pending, reviewed or resolved'}, status = 400)

    feedback.status = new_status
    feedback.save()

    return Response({
        'message': f'Feedback status updated to {new_status}',
        'feedback_id': feedback.id,
        'status': feedback.status,
    }, status = 200)