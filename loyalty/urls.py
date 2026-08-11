from django.urls import path
from loyalty import views


urlpatterns = [
    # Customer - points account
    path('my_account/', views.MyLoyaltyAccount),
    path('my_transactions/', views.MyLoyaltyTransactions),

    # Promotions - admin / branch manager
    path('promotions/create/', views.CreatePromotion),
    path('promotions/list/', views.ListPromotions),
    path('promotions/update/<int:promo_id>/', views.UpdatePromotion),
    path('promotions/delete/<int:promo_id>/', views.DeletePromotion),

    # Promotions - customer-facing (Shop browsing)
    path('promotions/active/', views.ActivePromotions),
]
