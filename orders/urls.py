from django.urls import path, include
from orders import views


urlpatterns = [
    # Cart
    path('view_cart/', views.ViewCart),
    path('add_to_cart/', views.AddToCart),
    path('update_cart_item/', views.UpdateCartItem),
    path('clear_cart/', views.ClearCart),
    path('remove_cart_item/', views.RemoveCartItem),

    # Orders
    path('place_order/', views.PlaceOrder),
    path('get_my_order/', views.GetMyOrder),
    path('cancel_order/', views.CancelOrder),
    path('my_orders/', views.MyOrders),

    # Brach manager order
    path('branch_orders/', views.BranchOrders),
    path('update_order_status/', views.UpdateOrderStatus),
    path('get_order/', views.GetOrder),
    path('all_orders/', views.AllOrders),

]