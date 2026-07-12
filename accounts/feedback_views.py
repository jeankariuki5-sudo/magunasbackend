from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from .models import Feedback
from .permissions import IsAdmin, IsBranchManager, IsCustomer
from .feedback_serializers import FeedbackSerializer


# ─── CUSTOMER FEEDBACK VIEWSET ────────────────────────────────────────────────

class CustomerFeedbackViewset(viewsets.ModelViewSet):
    serializer_class = FeedbackSerializer
    permission_classes = [IsCustomer]

    def get_queryset(self):
        try:
            customer = self.request.user
        except Exception:
            raise PermissionDenied("Only customers can access this endpoint")

        return (
            Feedback.objects
            .filter(customer = customer)
            .select_related('branch', 'order')
            .order_by('-created_at')
        )

    def perform_create(self, serializer):
        try:
            customer = self.request.user
        except Exception:
            raise PermissionDenied("Only customers can submit feedback")
        serializer.save(customer = customer)

    def destroy(self, request, *args, **kwargs):
        feedback = self.get_object()
        if feedback.status != 'pending':
            return Response(
                {'error': 'Only pending feedback can be deleted'},
                status = 400
            )
        return super().destroy(request, *args, **kwargs)


# ─── BRANCH MANAGER FEEDBACK VIEWSET ─────────────────────────────────────────

class BranchFeedbackViewset(viewsets.ModelViewSet):
    serializer_class = FeedbackSerializer
    permission_classes = [IsBranchManager]
    http_method_names = ['get', 'put', 'patch']  # no create or delete for managers

    def get_queryset(self):
        try:
            branch = self.request.user.managed_branch
        except Exception:
            raise PermissionDenied("You are not assigned to any branch")

        queryset = (
            Feedback.objects
            .filter(branch = branch)
            .select_related('customer', 'order')
            .order_by('-created_at')
        )

        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status = status_filter)

        return queryset

    def partial_update(self, request, *args, **kwargs):
        feedback = self.get_object()
        new_status = request.data.get('status')

        if not new_status:
            return Response({'error': 'status is required'}, status = 400)

        if new_status not in ['pending', 'reviewed', 'resolved']:
            return Response(
                {'error': 'status must be pending, reviewed or resolved'},
                status = 400
            )

        feedback.status = new_status
        feedback.save()

        return Response({
            'message': f'Feedback status updated to {new_status}',
            'feedback_id': feedback.id,
            'status': feedback.status,
        }, status = 200)


# ─── ADMIN FEEDBACK VIEWSET ───────────────────────────────────────────────────

class AdminFeedbackViewset(viewsets.ModelViewSet):
    serializer_class = FeedbackSerializer
    permission_classes = [IsAdmin]
    http_method_names = ['get', 'put', 'patch', 'delete']  # no create for admin

    def get_queryset(self):
        queryset = (
            Feedback.objects
            .select_related('customer', 'branch', 'order')
            .order_by('-created_at')
        )

        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status = status_filter)

        branch_filter = self.request.query_params.get('branch')
        if branch_filter:
            queryset = queryset.filter(branch_id = branch_filter)

        type_filter = self.request.query_params.get('feedback_type')
        if type_filter:
            queryset = queryset.filter(feedback_type = type_filter)

        return queryset

    def partial_update(self, request, *args, **kwargs):
        feedback = self.get_object()
        new_status = request.data.get('status')

        if not new_status:
            return Response({'error': 'status is required'}, status = 400)

        if new_status not in ['pending', 'reviewed', 'resolved']:
            return Response(
                {'error': 'status must be pending, reviewed or resolved'},
                status = 400
            )

        feedback.status = new_status
        feedback.save()

        return Response({
            'message': f'Feedback status updated to {new_status}',
            'feedback_id': feedback.id,
            'status': feedback.status,
        }, status = 200)