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
]