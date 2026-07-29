from django.urls import path
from products import views


urlpatterns = [
    # categories
    path('list_categories/', views.ListCategories),
    path('create_category/', views.CreateCategory),
    path('update_category/<int:category_id>/', views.UpdateCategory),
    path('delete_category/<int:category_id>/', views.DeleteCategory),


    # products
    path('list_products/', views.ListProducts),
    path('get_product/<int:product_id>/', views.GetProduct),
    path('create_product/', views.CreateProduct),
    path('update_product/<int:product_id>/', views.UpdateProduct),
    path('delete_product/<int:product_id>/', views.DeleteProduct),

    # Branch product
    # NOTE: removed the bare 'list_branch_products/' entry - ListBranchProducts
    # requires branch_id as a positional arg, so that URL could never have
    # worked (TypeError on every hit). Only the branch-scoped one is valid.
    path('list_branch_products/<int:branch_id>/', views.ListBranchProducts),
    path('add_branch_product/', views.AddBranchProduct),
    path('update_branch_product/<int:branch_product_id>/', views.UpdateBranchProduct),
    path('delete_branch_product/<int:branch_product_id>/', views.DeleteBranchProduct),
    path('my_branch_products/', views.MyBranchProducts),
]