from django.urls import path
from products import views


urlpatterns = [
    # categories
    path('list_categories/',views.ListCategories ),
    path('create_category/', views.CreateCategory),
    path('update_category/', views.UpdateCategory),
    path('delete_category/', views.DeleteCategory),


    # products
    path('list_products/', views.ListProducts),
    path('create_product/', views.CreateProduct),
    path('update_product/', views.UpdateProduct),
    path('delete_product/', views.DeleteProduct),

    # Branch product
    path('list_branch_products/', views.ListBranchProducts),
    path('add_branch_product/', views.AddBranchProduct),
    path('update_branch_product/', views.UpdateBranchProduct),
    path('delete_branch_product/', views.DeleteBranchProduct),
    path('my_branch_products/', views.MyBranchProducts),
]