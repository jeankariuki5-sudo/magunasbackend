from django.shortcuts import render
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from .haversine import CalculateDistance

from accounts.permissions import IsAdmin, IsAdminOrBranchManager, IsBranchManager
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



# ══════════════════════════════════════════════════════
# DELIVERY ZONE VIEWS
# ══════════════════════════════════════════════════════

# ─── LIST DELIVERY ZONES FOR A BRANCH (public) ────────────────────────────────

@api_view(['GET'])
@permission_classes([AllowAny])
def ListDeliveryZones(request, branch_id):
    try:
        branch = Branch.objects.get(id = branch_id)
    except Branch.DoesNotExist:
        return Response({'error': 'Branch not found'}, status = 404)

    zones = DeliveryZone.objects.filter(
        branch = branch,
        is_active = True
    ).order_by('zone_name')

    data = []
    for zone in zones:
        data.append({
            'id': zone.id,
            'zone_name': zone.zone_name,
            'delivery_fee': str(zone.delivery_fee),
            'is_active': zone.is_active,
        })

    return Response({
        'branch': branch.branch_name,
        'delivery_zones': data
    }, status = 200)


# ─── CREATE DELIVERY ZONE (branch manager for own branch, admin for any) ───────

@api_view(['POST'])
@permission_classes([IsAdminOrBranchManager])
def CreateDeliveryZone(request):
    zone_name = request.data.get('zone_name')
    delivery_fee = request.data.get('delivery_fee')

    if not zone_name or not delivery_fee:
        return Response({'error': 'zone_name and delivery_fee are required'}, status = 400)

    # Determine branch based on role
    if request.user.role == 'branch_manager':
        try:
            branch = request.user.managed_branch
        except Exception:
            return Response({'error': 'You are not assigned to any branch'}, status = 404)
    else:
        # Admin must provide branch_id
        branch_id = request.data.get('branch_id')
        if not branch_id:
            return Response({'error': 'branch_id is required for admin'}, status = 400)
        try:
            branch = Branch.objects.get(id = branch_id)
        except Branch.DoesNotExist:
            return Response({'error': 'Branch not found'}, status = 404)

    # NEW: Check duplicate zone name for this branch (case insensitive)
    if DeliveryZone.objects.filter(
        branch = branch,
        zone_name__iexact = zone_name
    ).exists():
        return Response({
            'error': f'Zone "{zone_name}" already exists for {branch.branch_name}'
        }, status = 400)

    zone = DeliveryZone.objects.create(
        branch = branch,
        zone_name = zone_name,
        delivery_fee = delivery_fee
    )

    return Response({
        'message': 'Delivery zone created successfully',
        'zone': {
            'id': zone.id,
            'branch': zone.branch.branch_name,
            'zone_name': zone.zone_name,
            'delivery_fee': str(zone.delivery_fee),
            'is_active': zone.is_active,
        }
    }, status = 201)


# ─── UPDATE DELIVERY ZONE (branch manager for own, admin for any) ──────────────

@api_view(['PUT'])
@permission_classes([IsAdminOrBranchManager])
def UpdateDeliveryZone(request, zone_id):
    try:
        zone = DeliveryZone.objects.select_related('branch').get(id = zone_id)
    except DeliveryZone.DoesNotExist:
        return Response({'error': 'Delivery zone not found'}, status = 404)

    # Branch manager can only update their own branch zones
    if request.user.role == 'branch_manager':
        try:
            branch = request.user.managed_branch
        except Exception:
            return Response({'error': 'You are not assigned to any branch'}, status = 404)
        if zone.branch != branch:
            return Response({'error': 'You can only update zones in your own branch'}, status = 403)

    new_zone_name = request.data.get('zone_name')

    # NEW: Check duplicate zone name excluding current zone
    if new_zone_name and DeliveryZone.objects.filter(
        branch = zone.branch,
        zone_name__iexact = new_zone_name
    ).exclude(id = zone_id).exists():
        return Response({
            'error': f'Zone "{new_zone_name}" already exists for {zone.branch.branch_name}'
        }, status = 400)

    zone.zone_name = new_zone_name or zone.zone_name
    zone.delivery_fee = request.data.get('delivery_fee', zone.delivery_fee)
    zone.is_active = request.data.get('is_active', zone.is_active)
    zone.save()

    return Response({
        'message': 'Delivery zone updated successfully',
        'zone': {
            'id': zone.id,
            'branch': zone.branch.branch_name,
            'zone_name': zone.zone_name,
            'delivery_fee': str(zone.delivery_fee),
            'is_active': zone.is_active,
        }
    }, status = 200)


# ─── DELETE DELIVERY ZONE (branch manager for own, admin for any) ──────────────

@api_view(['DELETE'])
@permission_classes([IsAdminOrBranchManager])
def DeleteDeliveryZone(request, zone_id):
    try:
        zone = DeliveryZone.objects.select_related('branch').get(id = zone_id)
    except DeliveryZone.DoesNotExist:
        return Response({'error': 'Delivery zone not found'}, status = 404)

    # Branch manager can only delete their own branch zones
    if request.user.role == 'branch_manager':
        try:
            branch = request.user.managed_branch
        except Exception:
            return Response({'error': 'You are not assigned to any branch'}, status = 404)
        if zone.branch != branch:
            return Response({'error': 'You can only delete zones in your own branch'}, status = 403)

    zone_name = zone.zone_name
    zone.delete()
    return Response({'message': f'Delivery zone "{zone_name}" deleted successfully'}, status = 200)


# ─── MY BRANCH DELIVERY ZONES (branch manager only) ───────────────────────────

@api_view(['GET'])
@permission_classes([IsBranchManager])
def MyBranchDeliveryZones(request):
    try:
        branch = request.user.managed_branch
    except Exception:
        return Response({'error': 'You are not assigned to any branch'}, status = 404)

    zones = DeliveryZone.objects.filter(branch = branch).order_by('zone_name')

    data = []
    for zone in zones:
        data.append({
            'id': zone.id,
            'zone_name': zone.zone_name,
            'delivery_fee': str(zone.delivery_fee),
            'is_active': zone.is_active,
        })

    return Response({
        'branch': branch.branch_name,
        'delivery_zones': data
    }, status = 200)



# ══════════════════════════════════════════════════════
# GEOLOCATION VIEWS
# ══════════════════════════════════════════════════════

# ─── FIND NEAREST BRANCH (public) ─────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([AllowAny])
def NearestBranch(request):
    """
    Takes customer lat/lng as query params.
    Returns nearest active branch using Haversine formula.
    Usage: /api/branches/nearest/?lat=-1.2676&lng=36.8108
    """
    latitude = request.query_params.get('lat')
    longitude = request.query_params.get('lng')

    if not latitude or not longitude:
        return Response({'error': 'lat and lng query parameters are required'}, status = 400)

    try:
        float(latitude)
        float(longitude)
    except ValueError:
        return Response({'error': 'lat and lng must be valid numbers'}, status = 400)

    branches = Branch.objects.filter(is_active = True)

    if not branches.exists():
        return Response({'error': 'No active branches found'}, status = 404)

    # Calculate distance to each branch
    branches_with_distance = []
    for branch in branches:
        distance = CalculateDistance(
            latitude, longitude,
            branch.latitude, branch.longitude
        )
        branches_with_distance.append({
            'id': branch.id,
            'branch_name': branch.branch_name,
            'address': branch.address,
            'phone_number': branch.phone_number,
            'latitude': str(branch.latitude),
            'longitude': str(branch.longitude),
            'distance_km': round(distance, 2),
        })

    # Sort by distance — nearest first
    branches_with_distance.sort(key = lambda x: x['distance_km'])

    return Response({
        'your_location': {
            'latitude': latitude,
            'longitude': longitude,
        },
        'nearest_branch': branches_with_distance[0],
        'all_branches': branches_with_distance,
    }, status = 200)


# ─── FIND NEAREST BRANCH WITH PRODUCT IN STOCK (public) ───────────────────────

@api_view(['GET'])
@permission_classes([AllowAny])
def NearestBranchWithProduct(request, product_id):
    """
    Takes customer lat/lng and product_id.
    Returns nearest branch that has the product in stock.
    Usage: /api/branches/nearest/product/1/?lat=-1.2676&lng=36.8108
    """
    latitude = request.query_params.get('lat')
    longitude = request.query_params.get('lng')

    if not latitude or not longitude:
        return Response({'error': 'lat and lng query parameters are required'}, status = 400)

    try:
        float(latitude)
        float(longitude)
    except ValueError:
        return Response({'error': 'lat and lng must be valid numbers'}, status = 400)

    # Find all branch products for this product that are in stock
    from products.models import BranchProduct, Product

    try:
        product = Product.objects.get(id = product_id, is_active = True)
    except Product.DoesNotExist:
        return Response({'error': 'Product not found'}, status = 404)

    branch_products = BranchProduct.objects.filter(
        product = product,
        is_available = True,
        stock_quantity__gt = 0
    ).select_related('branch')

    if not branch_products.exists():
        return Response({
            'error': f'"{product.product_name}" is out of stock at all branches'
        }, status = 404)

    # Calculate distance to each branch that has the product
    branches_with_distance = []
    for bp in branch_products:
        if not bp.branch.is_active:
            continue
        distance = CalculateDistance(
            latitude, longitude,
            bp.branch.latitude, bp.branch.longitude
        )
        branches_with_distance.append({
            'id': bp.branch.id,
            'branch_name': bp.branch.branch_name,
            'address': bp.branch.address,
            'phone_number': bp.branch.phone_number,
            'latitude': str(bp.branch.latitude),
            'longitude': str(bp.branch.longitude),
            'distance_km': round(distance, 2),
            'product': {
                'id': product.id,
                'product_name': product.product_name,
                'price': str(bp.price),
                'stock_quantity': bp.stock_quantity,
            }
        })

    if not branches_with_distance:
        return Response({
            'error': f'No active branches have "{product.product_name}" in stock'
        }, status = 404)

    # Sort by distance — nearest first
    branches_with_distance.sort(key = lambda x: x['distance_km'])

    return Response({
        'product': product.product_name,
        'your_location': {
            'latitude': latitude,
            'longitude': longitude,
        },
        'nearest_branch_with_stock': branches_with_distance[0],
        'all_branches_with_stock': branches_with_distance,
    }, status = 200)