from django.shortcuts import render
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsAdmin, IsBranchManager
from .models import Branch, DeliveryZone

User = get_user_model()

# Create your views here.
# ======================================= 
#  list all branches (public)
# =======================================
@api_view(['GET'])
@permission_classes([])
def ListBranches(request):
    branches = Branch.objects.filter(is_active=True)
    data = []
    for branch in branches:
        data.append({
            'id': branch.id,
            'branch_name': branch.branch_name,
            'address': branch.address,
            'phone_number': branch.phone_number,
            'latitude': str(branch.latitude),
            'longitude': str(branch.longitude),
            'branch_manager': branch.branch_manager.username if branch.branch_manager else None,
        })
    return Response(data, status=200)


# ==========================================
# Create branch (admin only)
# ==========================================
@api_view(['POST'])
@permission_classes([IsAdmin])
def CreateBranch(request):
    branch_name = request.data.get('branch_name')
    address = request.data.get('address')
    phone_number = request.data.get('phone_number', '')
    latitude = request.data.get('latitude')
    longitude = request.data.get('longitude')
    manager_id = request.data.get('manager_id')

    if not branch_name or not address or not latitude or not longitude:
        return Response({'error': 'branch_name, address, latitude and longitude are required'}, status=400)

    # Validate manager if provided
    manager = None
    if manager_id:
        try:
            manager = User.objects.get(id=manager_id, role='branch_manager')
        except User.DoesNotExist:
            return Response({'error': 'Branch manager not found or user is not a branch manager'}, status=404)

        # Check manager not already assigned to another branch
        if hasattr(manager, 'managed_branch'):
            return Response({'error': f'{manager.username} is already managing another branch'}, status=400)

    try:
        branch = Branch.objects.create(
            branch_name=branch_name,
            address=address,
            phone_number=phone_number,
            latitude=latitude,
            longitude=longitude,
            branch_manager=manager
        )

        return Response({
            'message': 'Branch created successfully',
            'branch': {
                'id': branch.id,
                'branch_name': branch.branch_name,
                'address': branch.address,
                'phone_number': branch.phone_number,
                'latitude': str(branch.latitude),
                'longitude': str(branch.longitude),
                'branch_manager': branch.branch_manager.username if branch.branch_manager else None,
            }
        }, status=201)

    except IntegrityError as e:
        return Response({'error': 'Database error: ' + str(e)}, status=400)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


# ===================================================
# Get single branch 
# ===================================================
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def GetBranch(request, branch_id):
    try:
        branch = Branch.objects.get(id=branch_id)
    except Branch.DoesNotExist:
        return Response({'error': 'Branch not found'}, status=404)

    return Response({
        'id': branch.id,
        'branch_name': branch.branch_name,
        'address': branch.address,
        'phone_number': branch.phone_number,
        'latitude': str(branch.latitude),
        'longitude': str(branch.longitude),
        'is_active': branch.is_active,
        'branch_manager': branch.branch_manager.username if branch.branch_manager else None,
    }, status=200)


# ==============================================
# Update Branch (admin only)
# ==============================================
@api_view(['PUT'])
@permission_classes([IsAdmin])
def UpdateBranch(request, branch_id):
    try:
        branch = Branch.objects.get(id=branch_id)
    except Branch.DoesNotExist:
        return Response({'error': 'Branch not found'}, status=404)

    branch.branch_name = request.data.get('branch_name', branch.branch_name)
    branch.address = request.data.get('address', branch.address)
    branch.phone_number = request.data.get('phone_number', branch.phone_number)
    branch.latitude = request.data.get('latitude', branch.latitude)
    branch.longitude = request.data.get('longitude', branch.longitude)
    branch.is_active = request.data.get('is_active', branch.is_active)

    # Reassign manager if provided
    manager_id = request.data.get('manager_id')
    if manager_id:
        try:
            manager = User.objects.get(id=manager_id, role='branch_manager')
        except User.DoesNotExist:
            return Response({'error': 'Branch manager not found or user is not a branch manager'}, status=404)

        if hasattr(manager, 'managed_branch') and manager.managed_branch != branch:
            return Response({'error': f'{manager.username} is already managing another branch'}, status=400)

        branch.branch_manager = manager

    branch.save()

    return Response({
        'message': 'Branch updated successfully',
        'branch': {
            'id': branch.id,
            'branch_name': branch.branch_name,
            'address': branch.address,
            'phone_number': branch.phone_number,
            'latitude': str(branch.latitude),
            'longitude': str(branch.longitude),
            'is_active': branch.is_active,
            'branch_manager': branch.branch_manager.username if branch.branch_manager else None,
        }
    }, status=200)


# =========================================================
# Delete branch (admin only)
# =========================================================
@api_view(['DELETE'])
@permission_classes([IsAdmin])
def DeleteBranch(request, branch_id):
    try:
        branch = Branch.objects.get(id=branch_id)
    except Branch.DoesNotExist:
        return Response({'error': 'Branch not found'}, status=404)

    branch.delete()
    return Response({'message': 'Branch deleted successfully'}, status=200)


# ================================================
#  Assign manager to existing branch (admin only)
# ================================================
@api_view(['POST'])
@permission_classes([IsAdmin])
def AssignManager(request, branch_id):
    try:
        branch = Branch.objects.get(id=branch_id)
    except Branch.DoesNotExist:
        return Response({'error': 'Branch not found'}, status=404)

    manager_id = request.data.get('manager_id')
    if not manager_id:
        return Response({'error': 'manager_id is required'}, status=400)

    try:
        manager = User.objects.get(id=manager_id, role='branch_manager')
    except User.DoesNotExist:
        return Response({'error': 'Branch manager not found or user is not a branch manager'}, status=404)

    if hasattr(manager, 'managed_branch') and manager.managed_branch != branch:
        return Response({'error': f'{manager.username} is already managing another branch'}, status=400)

    branch.branch_manager = manager
    branch.save()

    return Response({
        'message': f'{manager.username} assigned to {branch.branch_name} successfully',
        'branch': {
            'id': branch.id,
            'branch_name': branch.branch_name,
            'branch_manager': manager.username,
        }
    }, status=200)


# ====================================================
# List available managers (admin only)
# =====================================================

@api_view(['GET'])
@permission_classes([IsAdmin])
def ListManagers(request):
    managers = User.objects.filter(role='branch_manager')
    assigned_param = request.query_params.get('assigned')

    data = []
    for manager in managers:
        already_assigned = hasattr(manager, 'managed_branch')

        if assigned_param == 'false' and already_assigned:
            continue
        if assigned_param == 'true' and not already_assigned:
            continue

        data.append({
            'id': manager.id,
            'username': manager.username,
            'email': manager.email,
            'phone_number': manager.phone_number,
            'assigned': already_assigned,
            'branch': manager.managed_branch.branch_name if already_assigned else None,
        })

    return Response(data, status=200)


# ===============================================
# My branch (branch manager only)
# ===============================================

@api_view(['GET'])
@permission_classes([IsBranchManager])
def MyBranch(request):
    try:
        branch = request.user.managed_branch
    except Branch.DoesNotExist:
        return Response({'error': 'You have not been assigned a branch yet'}, status=404)

    return Response({
        'id': branch.id,
        'branch_name': branch.branch_name,
        'address': branch.address,
        'phone_number': branch.phone_number,
        'latitude': str(branch.latitude),
        'longitude': str(branch.longitude),
        'is_active': branch.is_active,
    }, status=200)
