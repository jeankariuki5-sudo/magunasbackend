from django.urls import path
from accounts import feedback_views



urlpatterns = [
    # Customer
    path('submit/', feedback_views.SubmitFeedback),
    path('my/', feedback_views.MyFeedback),
    path('my/<int:feedback_id>', feedback_views.GetMyFeedback),
    path('my/update/<int:feedback_id>/', feedback_views.UpdateMyFeedback),
    path('my/delete/<int:feedback_id>/', feedback_views.DeleteMyFeedback),

    # Branch manager
    path('branch/', feedback_views.BranchFeedback),
    path('branch/<int:feedback_id>/', feedback_views.GetBranchFeedback),
    path('branch/update_feedback_status/<int:feedback_id>/', feedback_views.UpdateBranchFeedbackStatus),
    path('Manager_submit/', feedback_views.ManagerSubmitFeedback),

    # Admin
    path('admin/', feedback_views.AllFeedback),
    path('admin/update_feedback_status/<int:feedback_id>/', feedback_views.AdminUpdateFeedbackStatus),

]