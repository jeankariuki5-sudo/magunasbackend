from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .feedback_views import  CustomerFeedbackViewset, BranchFeedbackViewset, AdminFeedbackViewset


router = DefaultRouter()
router.register('my', CustomerFeedbackViewset, basename = 'customer-feedback')
router.register('branch', BranchFeedbackViewset, basename = 'branch-feedback')
router.register('admin', AdminFeedbackViewset, basename = 'admin-feedback')

urlpatterns = [
    path('', include(router.urls)),
]