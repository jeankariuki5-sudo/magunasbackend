from django.urls import path
from branches import views


urlpatterns = [
    path('branch_list/', views.ListBranches),
    path('create_branch/', views.CreateBranch),
    path('get_branch/<int:branch_id>/', views.GetBranch),
    path('update_branch/<int:branch_id>/', views.UpdateBranch),
    path('delete_branch/<int:branch_id>/', views.DeleteBranch),
    path('assign_manager/<int:branch_id>/', views.AssignManager),
    path('list_managers/', views.ListManagers),
    path('my_branch/', views.MyBranch),

    # Delivery zones
    path('delivery_zones/<int:branch_id>/', views.ListDeliveryZones),
    path('delivery_zones/create/', views.CreateDeliveryZone),
    path('delivery_zones/update/<int:zone_id>/', views.UpdateDeliveryZone),
    path('delivery_zones/delete/<int:zone_id>/', views.DeleteDeliveryZone),
    path('delivery_zones/my_branch/', views.MyBranchDeliveryZones),

    # Geolocation
    path('nearest/', views.NearestBranch),
    path('nearest/product/<int:product_id>/', views.NearestBranchWithProduct),

]