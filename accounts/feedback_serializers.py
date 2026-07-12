from rest_framework import serializers
from .models import Feedback


class FeedbackSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(
        source = 'customer.username',
        read_only = True
    )
    branch_name = serializers.CharField(
        source = 'branch.branch_name',
        read_only = True
    )

    class Meta:
        model = Feedback
        fields = [
            'id',
            'customer_name',
            'branch_name',
            'order',
            'feedback_type',
            'title',
            'description',
            'status',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['status', 'created_at', 'updated_at', 'customer_name', 'branch_name']