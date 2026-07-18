from django.urls import path, include
from accounts import views, dashboard_views
from .dashboard_views import CustomerOrderHistory


urlpatterns = [
    # User auth
    path('auth/customer_register/',views.CustomerRegister ),
    path('auth/login/', views.Login),
    path('auth/logout/', views.Logout),
    path('auth/change_password/', views.ChangePassword),
    path('auth/reset_password/', views.ResetPassword),
    path('auth/forgot_password/', views.ForgotPassword),


    # Profile
    path('auth/me/', views.MyProfile ),
    path('auth/me/update_my_profile/', views.UpdateMyProfile),
    path('auth/me/delete/', views.DeleteMyAccount),


    # Admin
    path('auth/create_branch_manager/', views.CreateBranchManager),
    path('auth/list_users/', views.ListUsers),
    path('auth/get_user/<int:user_id>/', views.GetUser),
    # path('auth/delete/<int:user_id>/', views.AdminDeleteAdmin),
    path('auth/suspend_user/<int:id>/', views.SuspendUser),
    path('auth/unsuspend_user/<int:id>/', views.UnsuspendUser),
    path('auth/suspension_status/', views.SuspensionStatus),


    # Dashboard
    path('dashboard/admin/',  dashboard_views.AdminDashboard),
    path('dashboard/branch_manager/', dashboard_views.BranchManagerDashboard),
    path('dashboard/customer/', dashboard_views.CustomerDashboard),
    path('dashboard/customer/orders/', CustomerOrderHistory.as_view()),


    # feedback
    path('feedback/', include('accounts.feedback_urls')),

    # user acticity
    path('activity/', views.AllActivity),
    path('activity/failed_logins/', views.FailedLogins),
    path('users/activity/<int:user_id>/', views.UserActivity),
]