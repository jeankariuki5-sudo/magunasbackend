from django.urls import path
from payments import views


urlpatterns = [
    path("make_payment/<int:order_id>/", views.InitiatePayment),
    path('payment_status/', views.CheckPaymentStatus),
    path('callback/', views.MpesaCallback),
    path('view_all_payments/', views.AllPayments),
]