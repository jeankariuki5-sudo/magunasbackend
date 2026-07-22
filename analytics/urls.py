from django.urls import path
from analytics import views


urlpatterns = [
    # Admin
    path('revenue/branches/', views.RevenuePerBranch),
    path('products/top/', views.TopSellingProducts),
    path('orders/by_date/', views.OrdersByDate),

    # Branch Manager
    path('branch/revenue/', views.BranchRevenue),
    path('branch/products/top/', views.BranchTopProducts),
]