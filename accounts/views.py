from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.db import IntegrityError, transaction
from django.shortcuts import render
from django.contrib.auth import authenticate
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.db import models as db_models
from .models import ActivityLog
from .utils import GetClientIP

from .models import AccountSuspension, BranchManagerProfile, PasswordResetOTP, CustomerProfile, User
from .permissions import IsAdmin

# Create your views here.

# ========================================
# Customer registration
# ========================================
@api_view(['POST'])
@permission_classes([AllowAny])
@transaction.atomic
def CustomerRegister(request):
    username = request.data.get('username')
    email = request.data.get('email')
    phone_number = request.data.get('phone_number')
    password = request.data.get('password')
    password2 = request.data.get('password2')
    first_name = request.data.get('first_name')
    last_name = request.data.get('last_name')
    default_delivery_address = request.data.get('default_delivery_address', '')

    # Validate required fields
    if not all([username, email, password, password2, first_name, last_name]):
        return Response({'error': 'username, email, password, password2, first_name and last_name are required'}, status = 400)

    if password != password2:
        return Response({'error': 'Passwords do not match'}, status = 400)

    if User.objects.filter(username = username).exists():
        return Response({'error': 'Username already taken'}, status = 400)

    if User.objects.filter(email = email).exists():
        return Response({'error': 'Email already registered'}, status = 400)
    
    if User.objects.filter(phone_number = phone_number, is_active = True).exists():
        return Response({'error' : 'Phone number has already been registered'}, status = 400)

    try:
        # Create user
        user = User.objects.create_user(
            username = username,
            email = email,
            phone_number = phone_number or '',
            password = password,
            role = 'customer'
        )

        # Create customer profile
        profile = CustomerProfile.objects.create(
            user = user,
            first_name = first_name,
            last_name = last_name,
            default_delivery_address = default_delivery_address
        )

        refresh = RefreshToken.for_user(user)

        return Response({
            'message': 'Account created successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'phone_number': user.phone_number,
                'role': user.role,
            },
            'tokens': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }
        }, status = 201)

    except IntegrityError as e:
        return Response({'error': 'Database error: ' + str(e)}, status = 400)
    except Exception as e:
        return Response({'error': str(e)}, status = 500)
    


# =============================================
# Login
# =============================================
@api_view(['POST'])
@permission_classes([AllowAny])
def Login(request):
    username = request.data.get('username')
    password = request.data.get('password')
    ip = GetClientIP(request)

    if not username or not password:
        return Response({'message': 'Username and password are required'}, status = 400)
    
    # Check if username or email belongs to a suspended account
    suspended_user = User.objects.filter(
        db_models.Q(username=username) | db_models.Q(email=username),
        is_active=False
    ).first()

    if suspended_user and hasattr(suspended_user, 'suspension'):
        suspension = suspended_user.suspension

        # Auto-lift expired temporary suspensions
        if suspension.suspension_type == 'temporary' and suspension.lift_at:
            if timezone.now() >= suspension.lift_at:
                suspension.delete()
                suspended_user.is_active = True
                suspended_user.save()
            else:
                return Response({
                    'error': 'Your account has been suspended.',
                    'suspension_type': suspension.suspension_type,
                    'reason': suspension.reason,
                    'lift_at': suspension.lift_at,
                }, status=403)
        else:
            return Response({
                'error': 'Your account has been permanently suspended.',
                'reason': suspension.reason,
            }, status=403)

    user = authenticate(username = username, password = password)
    
    if not user:
        return Response({'message' : 'Invalid credentials'}, status = 401)
    
    ActivityLog.objects.create(
        user = user,
        action = 'login_success',
        ip_address = ip,
        detail = f'{user.role} logged in'
    )
    
    refresh = RefreshToken.for_user(user)

    return Response({
        'message' : 'Login Successful',
        'user' : {
            'username' : user.username,
            'email' : user.email,
            'phone_number' : user.phone_number,
            'role' : user.role,
        },
        'tokens' : {
            'access' : str(refresh.access_token),
            'refresh' : str(refresh),
        }
    }, status = 200)



# ==============================================================
# Create baranch manager account (admin only)
# ==============================================================
@api_view(['POST'])
@permission_classes([IsAdmin])
@transaction.atomic
def CreateBranchManager(request):
    username = request.data.get('username')
    email = request.data.get('email')
    phone_number = request.data.get('phone_number')
    password = request.data.get('password')
    first_name = request.data.get('first_name')
    last_name = request.data.get('last_name')
    national_id = request.data.get('national_id')

    if not all([username, email, password, first_name, last_name, national_id]):
        return Response({'error': 'username, email, password, first_name, last_name and national_id are required'}, status = 400)

    if User.objects.filter(username = username).exists():
        return Response({'error': 'Username already taken'}, status = 400)

    if User.objects.filter(email = email).exists():
        return Response({'error': 'Email already registered'}, status = 400)
    
    if User.objects.filter(phone_number = phone_number, is_active = True).exists():
        return Response({'error' : 'Phone number has already been registered'}, status = 400)

    if BranchManagerProfile.objects.filter(national_id = national_id).exists():
        return Response({'error': 'National ID already registered'}, status = 400)

    try:
        # Create user
        user = User.objects.create_user(
            username = username,
            email = email,
            phone_number = phone_number,
            password = password,
            role = 'branch_manager'
        )

        # Create manager profile
        profile = BranchManagerProfile.objects.create(
            user = user,
            first_name = first_name,
            last_name = last_name,
            national_id = national_id,
        )

        return Response({
            'message': 'Branch manager account created successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'phone_number': user.phone_number,
                'role': user.role,
            },
            'profile': {
                'first_name': profile.first_name,
                'last_name': profile.last_name,
                'national_id': profile.national_id,
            }
        }, status = 201)

    except IntegrityError as e:
        return Response({'error': 'Database error: ' + str(e)}, status = 400)
    except Exception as e:
        return Response({'error': str(e)}, status = 500)
    
    

# ========================================
# Show profile
# ========================================
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def MyProfile(request):
    user = request.user
    profile_data = {}

    if user.is_customer() and hasattr(user, 'customer_profile'):
        p = user.customer_profile
        profile_data = {
            'first_name': p.first_name,
            'last_name': p.last_name,
            'default_delivery_address': p.default_delivery_address,
        }
    elif user.is_branch_manager() and hasattr(user, 'manager_profile'):
        p = user.manager_profile
        profile_data = {
            'first_name': p.first_name,
            'last_name': p.last_name,
            'national_id': p.national_id,
        }

    return Response({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'phone_number': user.phone_number,
        'role': user.role,
        'profile': profile_data,
    }, status = 200)



# ==========================================
# Logout
# ==========================================
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def Logout(request):
    try:
        refresh_token =  request.data.get("refresh")
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response({"message" : "Logout successfull"})
    except TokenError:
        return Response({'error' : 'Invalid or expired token'})
    except Exception as e:
        return Response({'error' : str(e)})
    
    

# =======================================
# List all users (Admin Only)
# =======================================
@api_view(['GET'])
@permission_classes([IsAdmin])
def ListUsers(request):
    role = request.query_params.get('role')  # filter by role 
    users = User.objects.all()

    if role:
        users = users.filter(role = role)

    data = []
    for user in users:
        user_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'phone_number': user.phone_number,
            'role': user.role,
            'is_active': user.is_active,
            'profile': {}
        }

        if user.is_customer() and hasattr(user, 'customer_profile'):
            p = user.customer_profile
            user_data['profile'] = {
                'first_name': p.first_name,
                'last_name': p.last_name,
                'default_delivery_address': p.default_delivery_address,
            }
        elif user.is_branch_manager() and hasattr(user, 'manager_profile'):
            p = user.manager_profile
            user_data['profile'] = {
                'first_name': p.first_name,
                'last_name': p.last_name,
                'national_id': p.national_id,
            }

        data.append(user_data)

    return Response(data, status = 200)



# ===============================================
# Get a single user
# ===============================================
@api_view(['GET'])
@permission_classes([IsAdmin])
def GetUser(request, user_id):
    try:
        user = User.objects.get(id = user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)

    user_data = {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'phone_number': user.phone_number,
        'role': user.role,
        'is_active': user.is_active,
        'profile': {}
    }

    if user.is_customer() and hasattr(user, 'customer_profile'):
        p = user.customer_profile
        user_data['profile'] = {
            'first_name': p.first_name,
            'last_name': p.last_name,
            'default_delivery_address': p.default_delivery_address,
        }
    elif user.is_branch_manager() and hasattr(user, 'manager_profile'):
        p = user.manager_profile
        user_data['profile'] = {
            'first_name': p.first_name,
            'last_name': p.last_name,
            'national_id': p.national_id,
        }

    return Response(user_data, status = 200)



# ========================================================
# Update Profile
# ========================================================
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def UpdateMyProfile(request):
    user = request.user

    # Update user fields
    user.phone_number = request.data.get('phone_number', user.phone_number)
    user.email = request.data.get('email', user.email)

    # Check email and phone not taken by someone else
    new_email = request.data.get('email')
    if new_email and User.objects.filter(email=new_email).exclude(id=user.id).exists():
        return Response({'error': 'Email already registered to another account'}, status=400)
    
    new_phone = request.data.get('phone_number')
    if new_phone and User.objects.filter(phone_number=new_phone, is_active = True).exclude(id=user.id).exists():
        return Response({'error': 'Phone number already registered to another account'}, status=400)

    user.save()


    # Update profile fields based on role
    if user.is_customer() and hasattr(user, 'customer_profile'):
        p = user.customer_profile
        p.first_name = request.data.get('first_name', p.first_name)
        p.last_name = request.data.get('last_name', p.last_name)
        p.default_delivery_address = request.data.get('default_delivery_address', p.default_delivery_address)
        if 'profile_picture' in request.FILES:
            p.profile_picture = request.FILES['profile_picture']
        p.save()

        ActivityLog.objects.create(
            user = user,
            action = 'profile_updated',
            ip_address = GetClientIP(request),
            detail = 'Profile updated'
        )

        return Response({
            'message': 'Profile updated successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'phone_number': user.phone_number,
                'role': user.role,
            },
            'profile': {
                'first_name': p.first_name,
                'last_name': p.last_name,
                'default_delivery_address': p.default_delivery_address,
            }
        }, status=200)

    elif user.is_branch_manager() and hasattr(user, 'manager_profile'):
        p = user.manager_profile
        p.first_name = request.data.get('first_name', p.first_name)
        p.last_name = request.data.get('last_name', p.last_name)
        if 'profile_picture' in request.FILES:
            p.profile_picture = request.FILES['profile_picture']
        p.save()

        ActivityLog.objects.create(
            user = user,
            action = 'profile_updated',
            ip_address = GetClientIP(request),
            detail = 'Profile updated'
        )

        return Response({
            'message': 'Profile updated successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'phone_number': user.phone_number,
                'role': user.role,
            },
            'profile': {
                'first_name': p.first_name,
                'last_name': p.last_name,
                'national_id': p.national_id,  # national ID not editable
            }
        }, status=200)

    return Response({'message': 'User updated successfully'}, status = 200)



# ==========================================================
# Suspend account (admin only) 
# ==========================================================
@api_view(['POST'])
@permission_classes([IsAdmin])
def SuspendUser(request, user_id):
    try:
        user = User.objects.get(id = user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status = 404)

    if user == request.user:
        return Response({'error': 'You cannot suspend your own account'}, status = 400)

    suspension_type = request.data.get('suspension_type')  # permanent or temporary
    reason = request.data.get('reason')
    lift_at = request.data.get('lift_at')  # required if temporary e.g "2025-12-01T00:00:00Z"

    if not suspension_type or not reason:
        return Response({'error': 'suspension_type and reason are required'}, status = 400)

    if suspension_type not in ['permanent', 'temporary']:
        return Response({'error': 'suspension_type must be permanent or temporary'}, status = 400)

    if suspension_type == 'temporary' and not lift_at:
        return Response({'error': 'lift_at is required for temporary suspensions'}, status = 400)

    # Check if already suspended
    if hasattr(user, 'suspension'):
        return Response({'error': f'{user.username} is already suspended'}, status = 400)

    AccountSuspension.objects.create(
        user = user,
        suspension_type = suspension_type,
        reason = reason,
        suspended_by = request.user,
        lift_at = lift_at if suspension_type == 'temporary' else None
    )

    # Deactivate the account
    user.is_active = False
    user.save()

    return Response({
        'message': f'{user.username} has been suspended',
        'suspension': {
            'type': suspension_type,
            'reason': reason,
            'lift_at': lift_at if suspension_type == 'temporary' else 'Never',
        }
    }, status = 200)



# ===============================================
# Unsuspend account (admin only)
# ===============================================
@api_view(['POST'])
@permission_classes([IsAdmin])
def UnsuspendUser(request, user_id):
    try:
        user = User.objects.get(id = user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status = 404)

    if not hasattr(user, 'suspension'):
        return Response({'error': f'{user.username} is not suspended'}, status=400)

    suspension = user.suspension

    # Prevent unsuspending permanent suspensions without a reason
    if suspension.suspension_type == 'permanent':
        confirm = request.data.get('confirm')
        if confirm != 'yes':
            return Response({
                'error': 'This is a permanent suspension. Pass confirm=yes to lift it.'
            }, status = 400)

    suspension.delete()
    user.is_active = True
    user.save()

    return Response({'message': f'{user.username} has been unsuspended successfully'}, status=200)



# =============================================
# Get suspention status (admin only) 
# =============================================
@api_view(['GET'])
@permission_classes([IsAdmin])
def SuspensionStatus(request, user_id):
    try:
        user = User.objects.get(id = user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status = 404)

    if not hasattr(user, 'suspension'):
        return Response({'suspended': False, 'username': user.username}, status = 200)

    s = user.suspension
    return Response({
        'suspended': True,
        'username': user.username,
        'suspension_type': s.suspension_type,
        'reason': s.reason,
        'suspended_by': s.suspended_by.username if s.suspended_by else None,
        'suspended_at': s.suspended_at,
        'lift_at': s.lift_at if s.suspension_type == 'temporary' else 'Never',
    }, status = 200)



# =============================================================
# Change password (own account only)
# =============================================================
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ChangePassword(request):
    user = request.user
    old_password = request.data.get('old_password')
    new_password = request.data.get('new_password')
    new_password2 = request.data.get('new_password2')

    if not all([old_password, new_password, new_password2]):
        return Response({'error': 'old_password, new_password and new_password2 are required'}, status = 400)

    if not user.check_password(old_password):
        return Response({'error': 'Old password is incorrect'}, status = 400)

    if new_password != new_password2:
        return Response({'error': 'New passwords do not match'}, status = 400)

    user.set_password(new_password)
    user.save()

    ActivityLog.objects.create(
        user = user,
        action = 'profile_updated',
        ip_address = GetClientIP(request),
        detail = 'Profile updated'
    )

    return Response({'message': 'Password changed successfully'}, status = 200)



# ===================================================
# Request OTP 
# ===================================================
@api_view(['POST'])
@permission_classes([AllowAny])
def ForgotPassword(request):
    email = request.data.get('email')

    if not email:
        return Response({'error': 'Email is required'}, status=400)

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        # Don't reveal whether email exists or not — security best practice
        return Response({'message': 'If this email is registered, an OTP has been sent to it'}, status=200)

    # Generate OTP
    otp_obj = PasswordResetOTP.generate_otp(user)

    # Send email
    try:
        send_mail(
            subject='Magunas Supermarket — Password Reset OTP',
            message=f'''
Hello {user.username},

You requested a password reset for your Magunas account.

Your OTP is: {otp_obj.otp}

This OTP is valid for 10 minutes. Do not share it with anyone.

If you did not request this, ignore this email.

Magunas Supermarket
            ''',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception as e:
        return Response({'error': 'Failed to send email. Please try again later.'}, status=500)

    return Response({'message': 'If this email is registered, an OTP has been sent to it'}, status=200)


# ===============================================
# Verify otp and reset password
# ===============================================
@api_view(['POST'])
@permission_classes([AllowAny])
def ResetPassword(request):
    email = request.data.get('email')
    otp = request.data.get('otp')
    new_password = request.data.get('new_password')
    new_password2 = request.data.get('new_password2')

    if not all([email, otp, new_password, new_password2]):
        return Response({'error': 'email, otp, new_password and new_password2 are required'}, status = 400)

    if new_password != new_password2:
        return Response({'error': 'Passwords do not match'}, status = 400)

    try:
        user = User.objects.get(email = email)
    except User.DoesNotExist:
        return Response({'error': 'Invalid email or OTP'}, status = 400)

    # Find the latest unused OTP for this user
    try:
        otp_obj = PasswordResetOTP.objects.filter(
            user = user,
            otp = otp,
            is_used = False
        ).latest('created_at')
    except PasswordResetOTP.DoesNotExist:
        return Response({'error': 'Invalid email or OTP'}, status = 400)

    # Check expiry
    if not otp_obj.is_valid():
        return Response({'error': 'OTP has expired. Please request a new one.'}, status = 400)

    # Reset password
    user.set_password(new_password)
    user.save()

    # Mark OTP as used
    otp_obj.is_used = True
    otp_obj.save()

    return Response({'message': 'Password reset successfully. You can now log in.'}, status = 200)



# # ===================================================
# # Delete User (admin only)
# # ===================================================
# @api_view(['DELETE'])
# @permission_classes([IsAdmin])
# def AdminDeleteUser(request, user_id):
#     try:
#         user = User.objects.get(id = user_id)
#     except User.DoesNotExist:
#         return Response({'error': 'User not found'}, status = 404)

#     if user == request.user:
#         return Response({'error': 'You cannot delete your own account'}, status = 400)

#     username = user.username
#     user.delete()
#     return Response({'message': f'{username} deleted successfully'}, status = 200)


# =========================================
#  Delete my account 
# =========================================
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def DeleteMyAccount(request):
    user = request.user
    password = request.data.get('password')

    # Require password confirmation before deleting
    if not password:
        return Response({'error': 'Please confirm your password to delete your account'}, status = 400)

    if not user.check_password(password):
        return Response({'error': 'Incorrect password'}, status = 400)

    user.delete()
    return Response({'message': 'Your account has been deleted successfully'}, status = 200)


# =========================================================
# View user Activity
# =========================================================
@api_view(['GET'])
@permission_classes([IsAdmin])
def UserActivity(request, user_id):
    try:
        user = User.objects.get(id = user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status = 404)

    logs = ActivityLog.objects.filter(
        user = user
    ).order_by('-created_at')

    # Filter by action
    action_filter = request.query_params.get('action')
    if action_filter:
        logs = logs.filter(action = action_filter)

    data = []
    for log in logs:
        data.append({
            'id': log.id,
            'action': log.action,
            'ip_address': log.ip_address,
            'detail': log.detail,
            'created_at': log.created_at,
        })

    # Summary counts
    summary = {
        'total_logins': logs.filter(action = 'login_success').count(),
        'failed_logins': ActivityLog.objects.filter(
            ip_address__in = logs.values_list('ip_address', flat = True),
            action = 'login_failed'
        ).count(),
        'orders_placed': logs.filter(action = 'order_placed').count(),
        'orders_cancelled': logs.filter(action = 'order_cancelled').count(),
        'feedback_submitted': logs.filter(action = 'feedback_submitted').count(),
    }

    return Response({
        'user': user.username,
        'role': user.role,
        'summary': summary,
        'activity': data,
    }, status = 200)


# ====================================================
# View all failed logins (admin only)
# ====================================================
@api_view(['GET'])
@permission_classes([IsAdmin])
def FailedLogins(request):
    logs = ActivityLog.objects.filter(
        action = 'login_failed'
    ).order_by('-created_at')

    data = []
    for log in logs:
        data.append({
            'id': log.id,
            'detail': log.detail,
            'ip_address': log.ip_address,
            'created_at': log.created_at,
        })

    return Response(data, status = 200)



# ======================================================
# View all activity(admin only)
# ======================================================
@api_view(['GET'])
@permission_classes([IsAdmin])
def AllActivity(request):
    logs = ActivityLog.objects.select_related(
        'user'
    ).order_by('-created_at')

    action_filter = request.query_params.get('action')
    if action_filter:
        logs = logs.filter(action = action_filter)

    data = []
    for log in logs:
        data.append({
            'id': log.id,
            'user': log.user.username if log.user else 'Unknown',
            'action': log.action,
            'ip_address': log.ip_address,
            'detail': log.detail,
            'created_at': log.created_at,
        })

    return Response(data, status = 200)