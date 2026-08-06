from django.urls import path, include
from orders import views


urlpatterns = [
    # Cart
    path('view_cart/', views.ViewCart),
    path('add_to_cart/', views.AddToCart),
    path('update_cart_item/<int:cart_item_id>/', views.UpdateCartItem),
    path('clear_cart/', views.ClearCart),
    path('remove_cart_item/<int:cart_item_id>/', views.RemoveCartItem),

    # Orders
    path('place_order/', views.PlaceOrder),
    path('get_my_order/<int:order_id>/', views.GetMyOrder),
    path('cancel_order/<int:order_id>/', views.CancelOrder),
    path('my_orders/', views.MyOrders),

    # Branch manager order
    path('branch_orders/', views.BranchOrders),
    path('update_order_status/<int:order_id>/', views.UpdateOrderStatus),
    path('get_order/<int:order_id>/', views.GetOrder),
    path('all_orders/', views.AllOrders),

]